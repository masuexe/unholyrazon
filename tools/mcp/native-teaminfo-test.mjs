#!/usr/bin/env node
// Dedicated-server v6c native team-info contract. No standalone UIX.
import { existsSync, readFileSync, writeFileSync, appendFileSync, mkdtempSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawn } from "node:child_process";
import { createConnection, createServer } from "node:net";
import { loadResolvedProfile } from "../resolve-launch-profile.mjs";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const profileFile = resolve(root, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const { profile } = loadResolvedProfile(root, profileFile, process.env.UH_NATIVE_TEAMINFO_PROFILE || "mm8bdm-v6c-smoke");
const args = process.argv.slice(2);
if (args.length !== 2 || args[0] !== "--probe") {
  throw Error("Usage: node tools/mcp/native-teaminfo-test.mjs --probe PATH (see tools/README.md)");
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
const isolated = mkdtempSync(join(tmpdir(), "uh-native-teaminfo-"));
const transport = new StdioClientTransport({
  command: process.env.ZANDRONUM_NODE || process.execPath,
  args: [join(root, "tools/mcp/server-runner.mjs"), process.env.ZANDRONUM_MCP_SERVER || join(mcpDir, "dist/server.js")],
  cwd: isolated,
  env: { ...process.env, ZANDRONUM_LAUNCH_PROFILES: profileFile, ZANDRONUM_EXE: engine },
  stderr: "pipe",
});
transport.stderr?.on("data", chunk => process.stderr.write(chunk));
const client = new Client({ name: "uh-native-teaminfo-test", version: "1.0.0" });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let game;
let dedicated;
let serverOut = "";
let gamePort;
const serverLog = join(isolated, "server.log");
async function freePort() {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}
async function startDedicated() {
  gamePort = await freePort();
  const bridgePort = await freePort();
  dedicated = spawn(engine, ["-stdout", "-config", join(isolated,"server.ini"),
    "-iwad", profile.iwad, "-file", ...profile.files, "-host", "8", "-port", String(gamePort),
    "-lastmanstanding", "+set", "sv_updatemaster", "0", "+set", "sv_cheats", "1",
    "+set", "sv_lmscountdowntime", "3600", "+set", "bot_allowchat", "0",
    "+set", "lms_spectatorview", "1", "+set", "mm8bdm_sv_teaminfo", "1",
    "+map", profile.map, ...profile.extraArgs], {
    cwd:dirname(engine), env:{...process.env, ZANDRONUM_BRIDGE_PORT:String(bridgePort)},
    stdio:["pipe","pipe","pipe"],
  });
  for (const stream of [dedicated.stdout,dedicated.stderr]) stream.on("data", chunk => {
    serverOut += String(chunk); appendFileSync(serverLog,chunk);
  });
}
function sendServer(line) {
  if (dedicated.exitCode !== null || dedicated.signalCode !== null) throw Error(`Server exited: ${serverOut.slice(-3000)}`);
  dedicated.stdin.write(line + "\n");
}
async function serverCommand(line, pattern, timeout=10000) {
  const start = serverOut.length;
  sendServer(line);
  for (let elapsed=0; elapsed<timeout; elapsed+=100) {
    if (dedicated.exitCode !== null) throw Error(serverOut.slice(-3000));
    const match = serverOut.slice(start).match(pattern);
    if (match) return match;
    await delay(100);
  }
  throw Error(`Server command timed out: ${line}: ${serverOut.slice(-3000)}`);
}
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
    ...profile.extraArgs, "+playerclass", "Arcanist", "+name", "NativeTeamClient",
    "+set", "uh_cl_teaminfo", "0", "+set", "UIX_CL_Enable", "0",
    "+set", "mm8bdm_teaminfo", "1", "+set", "screenblocks", "11"], {
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
 await startDedicated();
 await launchHudEngine();
 await serverCommand("getmapvar uhtiova", /mapvar uhtiova = (-?\d+)/, 120000);
 await cmd(`connect 127.0.0.1:${gamePort}`);
 async function variable(name) { return (await call("get_map_var", {name})).structuredContent.value; }
 async function array(name,index) { return (await call("get_map_array", {name,index})).structuredContent.value; }
 async function waitFor(label, predicate, timeout=20000) {
   for (let elapsed=0; elapsed<timeout; elapsed+=500) {
     // ACS libraries temporarily disappear while a connection changes maps.
     try { if (await predicate()) return; } catch {}
     await delay(500);
   }
   throw Error(`Timed out: ${label}`);
 }
 await waitFor("spectator hello", async () => await variable("uhtiscorepolicy") >= 0);
 sendServer("addbot NativeAlly"); await delay(1000); sendServer("addbot NativeEnemy"); await delay(2000);
 sendServer("pukename ub_StartUpSettings");
 await delay(1000);
 await serverCommand("pukename UHTest_TI_Subject 1 0", /UH_TI_SUBJECT_READY 1 0/);
 await serverCommand("pukename UHTest_TI_Subject 2 2", /UH_TI_SUBJECT_READY 2 2/);
 sendServer("pukename uh_SetPlayerLifeStatus 2 2");
 async function probe(pn,variant) {
   await delay(800);
   await cmd(`pukename UHTest_TI_Check ${pn} ${variant}`);
   await delay(300);
   await cmd("echo UH_TI_FLUSH");
   check(await variable("tiProbeFailures") === 0, `Probe failed: ${logText().slice(-3000)}`);
 }
 await waitFor("native-only spectator health", async () => await array("uhtistathp",1) === 731);
 await probe(1,0); await probe(2,2);
 await cmd("join");
 await waitFor("client joined", async () => (await call("actor_state")).structuredContent.class === "Arcanist");
 sendServer("pukename uh_SetPlayerLifeStatus 0 1");
 await probe(1,0); await probe(2,3);
 await cmd("pukename UHTest_TI_LocalInventory 1"); await probe(1,0);
 await cmd("pukename UHTest_TI_ViewInfo"); await delay(300);
 console.log("Native renderer", {uhTeamMode:await variable("uhTeamMode"), weaponInitialized:await array("playerWeapons",7)});
 check(await array("playerWeapons",7) === 1, "Native teammate weapon renderer did not consume snapshot");
 if (process.env.UH_TEAMINFO_SCREENSHOT) {
   const shot = await call("screenshot");
   writeFileSync(resolve(process.env.UH_TEAMINFO_SCREENSHOT), Buffer.from(shot.content.find(c=>c.type==="image").data,"base64"));
 }
 await serverCommand("pukename UHTest_TI_Subject 1 1", /UH_TI_SUBJECT_READY 1 1/);
 await probe(1,1);
 await serverCommand("pukename UHTest_TI_Subject 1 2", /UH_TI_SUBJECT_READY 1 2/);
 await probe(1,2);
 await serverCommand("pukename UHTest_TI_Subject 1 4", /UH_TI_SUBJECT_READY 1 4/);
 await probe(1,4);
 if (process.env.UH_TEAMINFO_SCREENSHOT) {
   const shot = await call("screenshot");
   writeFileSync(resolve(process.env.UH_TEAMINFO_SCREENSHOT.replace(/\.png$/i,".wide.png")), Buffer.from(shot.content.find(c=>c.type==="image").data,"base64"));
 }
 await serverCommand("pukename UHTest_TI_Subject 1 5", /UH_TI_SUBJECT_READY 1 5/);
 await probe(1,5);
 await serverCommand("pukename UHTest_TI_Subject 1 2", /UH_TI_SUBJECT_READY 1 2/);
 await probe(1,2);
 sendServer("pukename uh_SetPlayerLifeStatus 1 2"); await probe(1,3);
 sendServer("pukename uh_SetPlayerLifeStatus 1 1"); await probe(1,2);
 sendServer("mm8bdm_sv_teaminfo 0"); await probe(1,3);
 sendServer("mm8bdm_sv_teaminfo 1"); await probe(1,2);
 await cmd("spectate"); await delay(1000);
 await probe(1,2); await probe(2,2);
 sendServer("lms_spectatorview 0"); await probe(1,3); await probe(2,3);
 sendServer("lms_spectatorview 1"); await probe(1,2);
 await cmd("disconnect"); await delay(500);
 await cmd(`connect 127.0.0.1:${gamePort}`);
 await waitFor("reconnect native snapshot", async () => await array("uhtistathp",1) === 619);
 await probe(1,2); await probe(2,2);
 sendServer("removebot NativeEnemy"); await probe(2,3); await probe(1,2);
 await cmd("pukename UHTest_TI_Order"); await delay(500); await cmd("echo UH_TI_FLUSH");
 check(await variable("tiProbeFailures") === 0, `Ordering probe failed: ${logText().slice(-3000)}`);
 check(!/UH_TI_FAIL |Runaway script|VM execution aborted|ACS execution error/.test(logText()+serverOut), "ACS runtime failure");
 console.log(logText().match(/UH_TI_(?:CHECK|ORDER)[^\n]*/g).join("\n"));
 console.log(JSON.stringify({status:"pass",nativeOnly:true,privacy:true,reconnect:true,ordering:true}));
} catch (e) {
 console.error(String(e)); process.exitCode=1;
 console.error(logText().slice(-6000));
} finally {
 if (attached) { try { await call("run_command", {text:"quit"}); } catch {} }
 if (game && game.exitCode === null) game.kill("SIGKILL");
 if (dedicated && dedicated.exitCode === null) dedicated.kill("SIGKILL");
 await client.close();
 if (process.exitCode) console.error(`Diagnostic logs retained: ${isolated}`);
 else rmSync(isolated, {recursive:true,force:true});
}
