#!/usr/bin/env node
// Focused v6c team palettes and shared-header runtime contracts. Offline only.
import { existsSync, readFileSync, mkdtempSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawn } from "node:child_process";
import { createConnection, createServer } from "node:net";
import { loadResolvedProfile } from "../resolve-launch-profile.mjs";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const profileFile = resolve(root, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const { profile } = loadResolvedProfile(root, profileFile, process.env.UH_COLORS_V6C_PROFILE || "mm8bdm-v6c-smoke");
const args = process.argv.slice(2);
if (args.length !== 2 || args[0] !== "--probe") {
  throw Error("Usage: node tools/mcp/colors-v6c-test.mjs --probe PATH (see tools/README.md)");
}
profile.files.push(resolve(args[1]));
profile.map = "MM2DW1";
const mcpDir = process.env.ZANDRONUM_MCP_DIR;
const engine = process.env.ZANDRONUM_EXE;
if (!mcpDir || !engine) throw Error("Set ZANDRONUM_MCP_DIR and ZANDRONUM_EXE, as for smoke-test.sh");
const sdkRoot = join(mcpDir, "node_modules/@modelcontextprotocol/sdk/dist/esm");
const [{ Client }, { StdioClientTransport }] = await Promise.all([
  import(pathToFileURL(join(sdkRoot, "client/index.js"))),
  import(pathToFileURL(join(sdkRoot, "client/stdio.js"))),
]);
const isolated = mkdtempSync(join(tmpdir(), "uh-colors-v6c-"));
const transport = new StdioClientTransport({
  command: process.env.ZANDRONUM_NODE || process.execPath,
  args: [join(root, "tools/mcp/server-runner.mjs"), process.env.ZANDRONUM_MCP_SERVER || join(mcpDir, "dist/server.js")],
  cwd: isolated,
  env: { ...process.env, ZANDRONUM_LAUNCH_PROFILES: profileFile, ZANDRONUM_EXE: engine },
  stderr: "pipe",
});
transport.stderr?.on("data", chunk => process.stderr.write(chunk));
const client = new Client({ name: "uh-colors-v6c-test", version: "1.0.0" });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let game;
let attached = false;
const engineLog = join(isolated, "engine.log");
const logText = () => existsSync(engineLog) ? readFileSync(engineLog, "utf8") : "";
async function launchHudEngine() {
  // This HUD profile can exceed the MCP launcher's fixed 42-second startup wait.
  // Own the process here, allow 120 seconds, then attach through the normal bridge.
  const port = await new Promise((resolve, reject) => {
    const reservation = createServer();
    reservation.once("error", reject);
    reservation.listen(0, "127.0.0.1", () => {
      const chosen = reservation.address().port;
      reservation.close(() => resolve(chosen));
    });
  });
  let stderr = "";
  game = spawn(engine, ["-stdout", "-config", join(isolated, "engine.ini"),
    "-iwad", profile.iwad, "-file", ...profile.files, "+map", profile.map,
    ...profile.extraArgs, "+playerclass", "Igniter"], {
    cwd: dirname(engine), env: {...process.env, ZANDRONUM_BRIDGE_PORT:String(port), ZANDRONUM_BRIDGE_LOG:engineLog},
    stdio:["ignore", "pipe", "pipe"],
  });
  game.stdout.on("data", () => {});
  game.stderr.on("data", data => { stderr = (stderr + data).slice(-4000); });
  game.on("error", error => { stderr += String(error); });
  for (let attempt = 0; attempt < 240; attempt++) {
    if (game.exitCode !== null || game.signalCode !== null) throw Error(`Engine exited ${game.exitCode ?? game.signalCode}: ${stderr} ${logText()}`);
    const ready = await new Promise(resolve => {
      const socket = createConnection({host:"127.0.0.1",port});
      socket.setTimeout(250);
      socket.once("connect", () => {socket.destroy(); resolve(true);});
      socket.once("error", () => {socket.destroy(); resolve(false);});
      socket.once("timeout", () => {socket.destroy(); resolve(false);});
    });
    if (ready) { await call("attach_instance", {port}); attached = true; return; }
    await delay(500);
  }
  throw Error(`Engine startup exceeded 120 seconds: ${stderr} ${logText()}`);
}

async function call(name, args = {}) {
  const result = await client.callTool(
    { name, arguments: { instance: 1, ...args } }, undefined, { timeout: 55000 },
  );
  if (result.isError) throw Error(JSON.stringify(result));
  return result;
}

async function cmd(text) {
  const result = await call("run_command", { text });
  console.log(text, JSON.stringify(result.content));
}


function check(ok, message) { if (!ok) throw Error(message); }
try {
 await client.connect(transport);
 await launchHudEngine();
 await call("set_pause", {paused:false});
 await call("step", {tics:35});
 await call("set_pause", {paused:false});
 await cmd("pukename UHTest_ColorsV6c"); await call("step", {tics:100});
 await cmd("echo UH_COLOR_FLUSH");
 const log = logText();
 check(/UH_COLOR_V6C checks=\d+ failures=0/.test(log), `Color/header contracts failed: ${log}`);
 check(!/UH_COLOR_FAIL |ACS:|Runaway script|VM execution aborted/.test(log), `Color runtime error: ${log}`);
 console.log(log.match(/UH_COLOR_V6C checks=\d+ failures=0/)[0]);
 console.log(JSON.stringify({status:"pass"}));
} catch (e) {
 console.error(String(e)); process.exitCode=1;
 console.error(logText().slice(-6000));
} finally {
 if (attached) { try { await call("run_command", {text:"quit"}); } catch {} }
 if (game && game.exitCode === null) game.kill("SIGKILL");
 await client.close();
 if (process.exitCode) console.error(`Diagnostic logs retained: ${isolated}`);
 else rmSync(isolated, {recursive:true,force:true});
}
