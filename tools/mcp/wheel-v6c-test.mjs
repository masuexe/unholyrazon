#!/usr/bin/env node
// Focused v6c class wheel contracts without standalone UIX. Offline only.
import { existsSync, readFileSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawn } from "node:child_process";
import { createConnection, createServer } from "node:net";
import { loadResolvedProfile } from "../resolve-launch-profile.mjs";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const profileFile = resolve(root, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const { profile } = loadResolvedProfile(root, profileFile, process.env.UH_WHEEL_V6C_PROFILE || "mm8bdm-v6c-smoke");
const args = process.argv.slice(2);
if (args.length !== 2 || args[0] !== "--probe") {
  throw Error("Usage: node tools/mcp/wheel-v6c-test.mjs --probe PATH (see tools/README.md)");
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
const isolated = mkdtempSync(join(tmpdir(), "uh-wheel-v6c-"));
const transport = new StdioClientTransport({
  command: process.env.ZANDRONUM_NODE || process.execPath,
  args: [join(root, "tools/mcp/server-runner.mjs"), process.env.ZANDRONUM_MCP_SERVER || join(mcpDir, "dist/server.js")],
  cwd: isolated,
  env: { ...process.env, ZANDRONUM_LAUNCH_PROFILES: profileFile, ZANDRONUM_EXE: engine },
  stderr: "pipe",
});
transport.stderr?.on("data", chunk => process.stderr.write(chunk));
const client = new Client({ name: "uh-wheel-v6c-test", version: "1.0.0" });
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
    ...profile.extraArgs, "+playerclass", "Arcanist"], {
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
 async function variable(name) { return (await call("get_map_var", {name})).structuredContent.value; }
 async function ticks(n=10) { await call("step", {tics:n}); }
 async function body(name) {
   await cmd(`playerclass ${name === "MegaManU" ? "MegaMan" : name}`); await cmd("map MM2DW1");
   await delay(500); await ticks(70);
   check((await call("actor_state")).structuredContent.class === name, `Wrong test body: ${name}`);
   await cmd("god");
 }
 async function open(route) {
   await cmd("+weapwheel"); await ticks();
   check(await variable("uhNativeWheel") === 1, "UH native adapter did not open");
   check(await variable("uhfw_route") === route, `Wrong class route: ${route}`);
   await cmd("pukename UHTest_WheelInspect 0"); await ticks();
   check(await variable("WHEEL_ITEMS_COUNT") === await variable("probeWheelItemCount"), "Native item IDs lost UH content");
 }
 async function close(mode=1) {
   await cmd("-weapwheel"); await ticks(35);
   check(await variable("uhNativeWheel") === 0, "UH native adapter did not close");
   check(await variable("uhww_own") === 0, "Wheel owner not released");
   await cmd(`pukename UHTest_WheelInspect ${mode}`); await ticks();
 }
 check((await call("actor_state")).structuredContent.class === "Arcanist", "Wrong initial test body");
 await cmd("god");
 await open(1);
 if (process.env.UH_WHEEL_SCREENSHOT) {
   const shot = await call("screenshot");
   writeFileSync(resolve(process.env.UH_WHEEL_SCREENSHOT), Buffer.from(shot.content.find(c => c.type === "image").data, "base64"));
 }
 await close();
 // Reopen and remove a held weapon while active; cancellation must not equip it.
 await open(1); await cmd("pukename UHTest_WheelRemove"); await ticks(35);
 check(await variable("uhNativeWheel") === 0, "Invalid fixed snapshot did not cancel");
 await cmd("pukename UHTest_WheelInspect 2"); await ticks(); await cmd("-weapwheel");
 for (const [name, route, kind] of [["Qwant",2,2],["NegaMan",3,3],["DecoyBot",4,0]]) {
   await body(name);
   if (kind) { await cmd(`pukename UHTest_WheelCopies ${kind}`); await ticks(35); }
   await open(route); await close();
 }
 // Unsupported classes retain the stock wheel rather than acquiring UH ownership.
 await body("MegaManU"); await cmd("+weapwheel"); await ticks();
 check(await variable("uhNativeWheel") === 0, "Stock fallback acquired UH ownership");
 check(await variable("WHEEL_ITEMS_COUNT") > 0, "Stock fallback did not populate");
 await cmd("-weapwheel"); await ticks(35);
 await cmd("echo UH_WHEEL_FLUSH");
 const log = logText();
 check((log.match(/UH_WHEEL_RESULT .*failures=0/g) || []).length === 5, `Missing class results: ${log}`);
 check(!/UH_WHEEL_FAIL |ACS:|Runaway script|VM execution aborted/.test(log), `Wheel runtime error: ${log}`);
 console.log(log.match(/UH_WHEEL_(?:CONTENT|RESULT)[^\n]*/g).join("\n"));
 console.log(JSON.stringify({status:"pass",classRoutes:4,cancellation:true,stockFallback:true}));
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
