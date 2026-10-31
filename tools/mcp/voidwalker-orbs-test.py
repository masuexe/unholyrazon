#!/usr/bin/env python3
"""Destructible orb regression: real damage, morph lifecycle and remote inventory."""
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
OUT = ROOT / "out/voidwalker-orbs-test"


def wait_until(predicate, seconds=120):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(.2)
    raise RuntimeError("timed out waiting for test condition")


class Bridge:
    def __init__(self, port):
        self.socket = socket.create_connection(("127.0.0.1", port), 2)
        self.socket.settimeout(15)
        self.stream = self.socket.makefile("rb")
        self.stream.readline()
        self.serial = 0

    def command(self, command):
        self.serial += 1
        marker = f"VWO_DONE_{self.serial}"
        self.socket.sendall((json.dumps({"t": "cmd", "text": command + "; echo " + marker}) + "\n").encode())
        output = []
        while True:
            line = self.stream.readline()
            if not line:
                raise RuntimeError("engine bridge disconnected")
            message = json.loads(line.decode(errors="replace"))
            if message.get("t") == "out":
                text = message.get("text", "")
                if marker in text:
                    return "".join(output)
                output.append(text)

    def close(self):
        self.stream.close()
        self.socket.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fixture = ROOT / "tools/mcp/fixtures/voidwalker-orbs"
    acc = shutil.which(os.environ.get("ACC", "acc"))
    if not acc:
        raise RuntimeError("ACC not found")
    obj = OUT / "VWOPROBE.o"
    with (OUT / "compile.log").open("w") as log:
        subprocess.run([acc, "-i", str(Path(acc).resolve().parent),
                        "-i", str(ROOT / "src/acs_source/v6b_overrides/_includes/common"),
                        str(fixture / "probe.acs"), str(obj)],
                       check=True, stdout=log, stderr=subprocess.STDOUT)
    addon = OUT / "probe.pk3"
    with ZipFile(addon, "w") as archive:
        archive.write(obj, "acs/VWOPROBE.o")
        for name in ("LOADACS", "DECORATE"):
            archive.write(fixture / name, name)
    profile = json.loads((ROOT / "tools/mm8bdm-v6c.launch.json").read_text())["mm8bdm-v6c-smoke"]
    engine = os.environ["ZANDRONUM_EXE"]
    files = [str((ROOT / p).resolve()) for p in profile["files"]] + [str(addon)]
    base = [engine, "-iwad", str((ROOT / profile["iwad"]).resolve()), "-file", *files,
            "-nosound", "+set", "fullscreen", "0", "+set", "vid_renderer", "0",
            "+set", "vid_defwidth", "640", "+set", "vid_defheight", "480",
            "+set", "sv_cheats", "1", "+map", profile["map"]]
    processes, handles, phases = [], [], []
    bridge = None

    def log(role):
        return (OUT / (role + ".log")).read_text(errors="replace")

    try:
        for role, port, extra in [
            ("server", 17952, ["-stdout", "-host", "8", "-port", "10950", "-lastmanstanding",
                               "+set", "sv_updatemaster", "0", "+set", "sv_noplayertimeout", "1",
                               "+set", "sv_lmscountdowntime", "300"]),
            ("client", 17951, ["-port", "10951", "+name", "OrbClient", "+playerclass", "MegaManU"]),
        ]:
            handle = (OUT / (role + ".log")).open("w")
            handles.append(handle)
            env = dict(os.environ, ZANDRONUM_BRIDGE_PORT=str(port))
            env.setdefault("DISPLAY", ":0")
            processes.append(subprocess.Popen(base + ["-config", str(OUT / (role + ".ini"))] + extra,
                             cwd=OUT, env=env, stdin=subprocess.PIPE, stdout=handle, stderr=handle))
        server, client = processes

        def server_command(command):
            if server.poll() is not None:
                raise RuntimeError("server exited: " + log("server")[-3000:])
            server.stdin.write((command + "\n").encode())
            server.stdin.flush()
            time.sleep(.25)

        def attach():
            if client.poll() is not None:
                raise RuntimeError("client exited: " + log("client")[-3000:])
            try:
                return Bridge(17951)
            except OSError:
                return None

        def run(script, args, marker, seconds=20):
            start = len(log("server"))
            server_command("pukename " + script + (" " + args if args else ""))
            wait_until(lambda: marker in log("server")[start:], seconds)
            chunk = log("server")[start:]
            if "VWO_FAIL" in chunk or re.search(r"failures=[1-9]", chunk):
                raise RuntimeError(chunk)
            phases.append(script)
            print("PASS " + script, flush=True)
            return chunk

        def box_ids():
            actors = bridge.command("actorsnear 2048")
            return [int(tid) for tid in re.findall(r"^near VWOrbHitbox (\d+) ", actors, re.M)]

        def client_check(phase):
            start = len(log("client"))
            bridge.command(f"pukename VWO_ClientCheck {phase}")
            wait_until(lambda: f"VWO_CLIENT phase={phase}" in log("client")[start:], 5)
            chunk = log("client")[start:]
            if "ok=1" not in chunk:
                raise RuntimeError("remote inventory check failed: " + chunk)
            phases.append(f"remote inventory {phase}")
            print("PASS " + phases[-1], flush=True)

        print("Waiting for dedicated server and remote client", flush=True)
        bridge = wait_until(attach, 180)
        wait_until(lambda: "*** " + profile["map"] in log("server"), 180)
        bridge.command("connect 127.0.0.1:10950")
        wait_until(lambda: "Snapshot received." in log("client"), 90)
        bridge.command("join")
        wait_until(lambda: "OrbClient joined the game." in log("server"), 30)
        server_command("addbot Metalman")
        server_command("addbot Cutman")
        time.sleep(1)
        # unholy is loaded before rz_debug, so this bridge variable is the
        # authoritative round divisor used by the named health query.
        server_command("setmapvar multibosscheck 1")
        run("VWO_HealthQuery", "5520 3", "VWO_HEALTH_QUERY_DONE")
        run("VWO_Setup", "", "VWO_SETUP class=VoidWalker")
        time.sleep(4)
        ids = box_ids()
        if len(ids) != 4:
            raise RuntimeError(f"expected four replicated hitboxes, got {ids}: " + bridge.command("actorsnear 2048"))
        for tid in ids:
            run("VWO_Record", str(tid), "VWO_BOX")
        client_check(0)
        run("VWO_DamageChecks", "", "VWO_DAMAGE_DONE")
        run("VWO_MarkerCheck", "", "VWO_MARKER_DONE")
        server_command("addbot Elecman")
        server_command("addbot Fireman")
        time.sleep(1)
        run("VWO_SnapshotCheck", "", "VWO_SNAPSHOT_DONE")
        run("VWO_DestroyChecks", "", "VWO_DESTROY_DONE")
        client_check(1)
        bridge.command("+attack")
        time.sleep(.8)
        bridge.command("-attack")
        run("VWO_Shots", "", "VWO_SHOTS_DONE")
        server_command("setmapvar multibosscheck 3")
        run("VWO_HealthQuery", "5263 5 385", "VWO_HEALTH_QUERY_DONE")
        server_command("setmapvar multibosscheck 0")
        run("VWO_HealthQuery", "4750 5", "VWO_HEALTH_QUERY_DONE")
        server_command("setmapvar multibosscheck 1")
        run("VWO_HealthQuery", "6290 5", "VWO_HEALTH_QUERY_DONE")
        run("VWO_Remorph", "0", "VWO_REMORPH_DONE")
        time.sleep(4)
        restored = box_ids()
        if len(restored) != 4:
            raise RuntimeError(f"remorph expected four replicated hitboxes, got {restored}")
        for tid in restored:
            run("VWO_Record", str(tid), "VWO_BOX")
        run("VWO_SpawnHealthCheck", "6290", "VWO_SPAWN_HEALTH_DONE")
        server_command("setmapvar multibosscheck 2")
        run("VWO_HealthQuery", "5520 5", "VWO_HEALTH_QUERY_DONE")
        run("VWO_Remorph", str(restored[0]), "VWO_REMORPH_DONE")
        time.sleep(4)
        restored = box_ids()
        if len(restored) != 4:
            raise RuntimeError("stale death revoked a newly restored element")
        for tid in restored:
            run("VWO_Record", str(tid), "VWO_BOX")
        run("VWO_SpawnHealthCheck", "5520", "VWO_SPAWN_HEALTH_DONE")
        client_check(0)
        result = run("VWO_Cleanup", "", "VWO_FINAL")
        wait_until(lambda: not box_ids(), 5)
        if any(error in log("server") + log("client") for error in ("Runaway script", "VM execution aborted")):
            raise RuntimeError("ACS runtime error")
        print(json.dumps({"status": "pass", "result": re.search(r"VWO_FINAL checks=\d+ failures=0", result)[0],
                          "phases": phases, "logs": str(OUT)}), flush=True)
    finally:
        if bridge:
            bridge.close()
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait()
        for handle in handles:
            handle.close()
        (OUT / "results.json").write_text(json.dumps(phases, indent=2))


if __name__ == "__main__":
    main()
