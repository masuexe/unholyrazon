#!/usr/bin/env python3
"""Focused dedicated-server/remote-client X-Ray regression via the engine bridge.

Uses the tracked smoke profile plus a temporary diagnostic library; never starts
UH_XRayVisionManager manually. Needs the bridge engine, ACC and loopback sockets.
"""
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out/xray-test"


def wait_until(predicate, seconds=120):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(.2)
    raise RuntimeError("timed out waiting for test condition")


class Bridge:
    def __init__(self, port):
        self.socket = socket.create_connection(("127.0.0.1", port), 2)
        self.socket.settimeout(15)
        self.stream = self.socket.makefile("rb")
        self.stream.readline()
        self.serial = 0

    def command(self, text):
        self.serial += 1
        marker = f"XR_DONE_{self.serial}"
        self.socket.sendall((json.dumps({"t": "cmd", "text": text + "; echo " + marker},
                                       separators=(",", ":")) + "\n").encode())
        lines = []
        while True:
            line = self.stream.readline()
            if not line:
                raise RuntimeError("engine bridge disconnected")
            msg = json.loads(line.decode(errors="replace"))
            if msg.get("t") == "out":
                output = msg.get("text", "")
                if marker in output:
                    return "".join(lines)
                lines.append(output)

    def close(self):
        self.stream.close()
        self.socket.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    profile = json.loads((ROOT / "tools/mm8bdm-v6c.launch.json").read_text())["mm8bdm-v6c-smoke"]
    engine = os.environ["ZANDRONUM_EXE"]
    acc = shutil.which(os.environ.get("ACC", "acc"))
    if not acc:
        raise RuntimeError("ACC not found")
    probe = OUT / "XRPROBE.o"
    subprocess.run([acc, "-i", str(Path(acc).resolve().parent),
                    str(ROOT / "tools/mcp/fixtures/xray-probe.acs"), str(probe)],
                   check=True, stdout=(OUT / "compile.log").open("w"), stderr=subprocess.STDOUT)
    addon = OUT / "probe.pk3"
    with ZipFile(addon, "w") as archive:
        archive.write(probe, "acs/XRPROBE.o")
        archive.writestr("LOADACS", "XRPROBE\n")
    files = [str((ROOT / p).resolve()) for p in profile["files"]] + [str(addon)]
    base = [engine, "-iwad", str((ROOT / profile["iwad"]).resolve()), "-file", *files,
            "-nosound", "+set", "fullscreen", "0", "+set", "vid_renderer", "0",
            "+set", "vid_defwidth", "640", "+set", "vid_defheight", "480",
            "+set", "sv_cheats", "1", "+map", profile["map"]]
    processes = []
    handles = []
    bridge = None
    results = []
    try:
        for role, port, extra in [
            ("server", 17932, ["-stdout", "-host", "8", "-port", "10930", "-lastmanstanding",
                               "+set", "sv_updatemaster", "0", "+set", "sv_noplayertimeout", "1",
                               "+set", "sv_lmscountdowntime", "300"]),
            ("client", 17931, ["-port", "10931", "+name", "XRClient"]),
        ]:
            log = (OUT / (role + ".log")).open("w")
            handles.append(log)
            env = dict(os.environ, ZANDRONUM_BRIDGE_PORT=str(port))
            env.setdefault("DISPLAY", ":0")
            p = subprocess.Popen(base + ["-config", str(OUT / (role + ".ini"))] + extra,
                                 stdin=subprocess.PIPE, stdout=log, stderr=log, cwd=OUT, env=env)
            processes.append(p)
        server, client = processes

        def server_command(command):
            if server.poll() is not None:
                raise RuntimeError("server exited")
            server.stdin.write((command + "\n").encode())
            server.stdin.flush()
            time.sleep(.3)

        def connect_bridge():
            if client.poll() is not None:
                raise RuntimeError("client exited; see client.log")
            try:
                return Bridge(17931)
            except OSError:
                return None

        print("Waiting for engine startup", flush=True)
        bridge = wait_until(connect_bridge, 180)
        wait_until(lambda: "*** " + profile["map"] in (OUT / "server.log").read_text(errors="replace"), 180)
        bridge.command("connect 127.0.0.1:10930")
        wait_until(lambda: "Snapshot received." in (OUT / "client.log").read_text(errors="replace"), 90)
        server_command("addbot Metalman")
        bridge.command("join")
        wait_until(lambda: "XRClient joined the game." in (OUT / "server.log").read_text(errors="replace"), 30)
        time.sleep(2)
        server_command("pukename ub_StartUpSettings")
        time.sleep(1)
        server_command("pukename XR_Setup 0 1")
        server_command("pukename rz_WatchTwoPlayerLeft")

        def renderer_count():
            return len(re.findall(r'script "UH_XRayVisionManager":', bridge.command("scriptstat")))

        def labels():
            # The teammate bar also names Metalman, but its X is 0.1. Require
            # the projected name and matching distance away from that bar.
            hud = bridge.command("dumphud")
            rows = re.findall(r"^msg 1 ([\d.-]+) ([\d.-]+) \d+ (.*)$", hud, re.M)
            projected = [s for x, y, s in rows if float(x) > 32 and float(y) > 100]
            return any("Metalman" in s for s in projected) and "1024" in projected

        def check(name, predicate, seconds=8):
            wait_until(predicate, seconds)
            results.append({"phase": name, "pass": True})
            print("PASS " + name, flush=True)

        check("late join starts renderer and draws target", lambda: renderer_count() == 1 and labels())
        bridge.command("pukename XR_StopRenderer")
        check("server retry recovers stopped renderer", lambda: renderer_count() == 1 and labels())
        print("Checking repeated delivery beyond old 30-second window", flush=True)
        time.sleep(32)
        check("one renderer after repeated delivery", lambda: renderer_count() == 1 and labels())
        server_command("rz_sv_twoplayerxray 0")
        check("cvar off clears target", lambda: not labels())
        server_command("rz_sv_twoplayerxray 1")
        check("cvar on restores target", labels)
        server_command("setmaparray totalplayersarr 1 3")
        check("three-player condition clears target", lambda: not labels())
        server_command("setmaparray totalplayersarr 1 2")
        check("two-player condition restores target", labels)
        server_command("rz_sv_twoplayerxray 0")
        check("round source cleared before event", lambda: not labels())
        bridge.command("pukename XR_StopRenderer")
        time.sleep(.3)
        server_command("pukename XR_Event 1")
        check("event source starts renderer independently", lambda: renderer_count() == 1 and labels())
        server_command("pukename XR_Event 0")
        check("event source clears target", lambda: not labels())
        server_command("rz_sv_twoplayerxray 1")
        check("round source restored", labels)
        # Reconnect to a server whose OPEN scripts have long since run. Its
        # connected client must recover without running any renderer manually.
        bridge.command("disconnect")
        time.sleep(1)
        bridge.command("connect 127.0.0.1:10930")
        time.sleep(5)
        bridge.command("join")
        time.sleep(2)
        server_command("pukename ub_StartUpSettings")
        time.sleep(1)
        server_command("pukename XR_Setup 0 1")
        check("reconnect restores one renderer and target", lambda: renderer_count() == 1 and labels(), 15)
        print(json.dumps({"status": "pass", "phases": results, "logs": str(OUT)}, ensure_ascii=False), flush=True)
    finally:
        if bridge:
            bridge.close()
        for p in processes:
            if p.poll() is None:
                p.kill()
            p.wait()
        for f in handles:
            f.close()
        (OUT / "results.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
