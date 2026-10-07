#!/usr/bin/env node
//
// DLC Centaurman option regression through a dedicated server and remote client.
// Covers visibility, per-owner slots, facing, shots, repair, cleanup and reconnect.
// Usage: node tools/mcp/centaur-option-test.mjs [--profile NAME] [--json]
// Env: ZANDRONUM_MCP_DIR, ZANDRONUM_EXE, ZANDRONUM_LAUNCH_PROFILES.

import { spawn } from "node:child_process";
import { appendFileSync, cpSync, existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { launchInstanceArgs, loadResolvedProfile } from "../resolve-launch-profile.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const PROFILES = process.env.ZANDRONUM_LAUNCH_PROFILES || join(ROOT, "tools/mm8bdm-v6b-linux.launch.json");
const MCP_DIR = process.env.ZANDRONUM_MCP_DIR;
const ENGINE = process.env.ZANDRONUM_EXE;
const SERVER = process.env.ZANDRONUM_MCP_SERVER || (MCP_DIR ? join(MCP_DIR, "dist/server.js") : "");
const RUNNER = join(ROOT, "tools/mcp/server-runner.mjs");
const SDK = join(MCP_DIR || "", "node_modules/@modelcontextprotocol/sdk/dist/esm");
const SERVER_LOG = "/tmp/centaur-option-server.log";

const options = { profile: "mm8bdm-v6b-smoke", gamePort: 10817, bridgePort: Number(process.env.ZANDRONUM_BRIDGE_PORT || 7777), json: false };
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === "--help" || arg === "-h") { process.stdout.write(usage()); process.exit(0); }
  if (arg === "--json") { options.json = true; continue; }
  if (arg === "--profile") { options.profile = process.argv[++i]; continue; }
  if (arg === "--game-port") { options.gamePort = Number.parseInt(process.argv[++i], 10); continue; }
  if (arg === "--bridge-port") { options.bridgePort = Number.parseInt(process.argv[++i], 10); continue; }
  throw new Error("unknown option " + arg);
}
if (!options.profile) throw new Error("invalid --profile");
for (const port of [options.gamePort, options.bridgePort]) {
  if (!Number.isInteger(port) || port < 1024 || port > 65435) throw new Error("invalid port");
}
for (const path of [SERVER, ENGINE, PROFILES, RUNNER, SDK]) if (!path || !existsSync(path)) {
  console.error("set ZANDRONUM_MCP_DIR / ZANDRONUM_EXE; missing: " + path);
  process.exit(2);
}

function usage() {
  return "Usage: centaur-option-test.mjs [--profile NAME] [--game-port N] [--bridge-port N] [--json]\n" +
    "Verify DLC Centaurman option actors on the remote client of a dedicated server.\n" +
    "Requires the bridge-patched engine and local TCP/UDP ports.\n";
}

const [{ Client }, { StdioClientTransport }] = await Promise.all([
  import(pathToFileURL(join(SDK, "client/index.js"))),
  import(pathToFileURL(join(SDK, "client/stdio.js"))),
]);
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [RUNNER, SERVER],
  cwd: MCP_DIR,
  env: { ...process.env, ZANDRONUM_EXE: ENGINE, ZANDRONUM_LAUNCH_PROFILES: PROFILES, ZANDRONUM_BRIDGE_PORT: String(options.bridgePort) },
  stderr: "ignore",
});

const client = new Client({ name: "unholy-centaur-option", version: "1.0.0" });
const delay = ms => new Promise(r => setTimeout(r, ms));
const launched = [];
let dedicated;
let dedicatedLog = "";
let isolatedRoot;
const text = result => (result.content || []).filter(x => x.type === "text").map(x => x.text).join("\n");

async function tool(name, args, timeout) {
  const result = await client.callTool({ name, arguments: args }, undefined, { timeout: timeout || 90_000 });
  if (result.isError) throw new Error(name + ": " + text(result));
  return result;
}

const checks = [];
let result;
try {
  const { profile: profileData } = loadResolvedProfile(ROOT, PROFILES, options.profile);

  // Dedicated -lastmanstanding server (the round actually starts, so roles and
  // the status snapshot are pushed to the remote client).
  // Isolated engine folder: the dedicated server must not share runtime/config
  // files with the MCP-controlled client.
  isolatedRoot = mkdtempSync(join(tmpdir(), "unholy-centaur-option-"));
  const serverDir = join(isolatedRoot, "server");
  cpSync(dirname(ENGINE), serverDir, { recursive: true });
  writeFileSync(SERVER_LOG, "");
  const common = ["-nosound", "+set", "vid_renderer", "0", "+set", "fullscreen", "0"];
  const serverArgs = [
    "-stdout", "-iwad", profileData.iwad, "-file", ...(profileData.files || []),
    "-host", "8", "-port", String(options.gamePort), "-lastmanstanding",
    "+set", "sv_minplayers", "5", "+set", "sv_updatemaster", "0", "+set", "sv_noplayertimeout", "1",
    "+set", "sv_cheats", "1", "+set", "uh_sv_loglevel", "4",
    "+set", "uh_sv_multiboss", "2",
    "+set", "uh_sv_forcedboss1", "111", "+set", "uh_sv_forcedboss2", "111",
    "+set", "uh_sv_forcebossplayer1", "0", "+set", "uh_sv_forcebossplayer2", "1",
    "+map", profileData.map || "MM2DW1", ...common,
  ];
  dedicated = spawn(join(serverDir, "zandronum"), serverArgs, {
    cwd: serverDir,
    env: { ...process.env, SDL_VIDEODRIVER: "offscreen", ZANDRONUM_BRIDGE_PORT: String(options.gamePort + 100) },
    stdio: ["pipe", "pipe", "pipe"],
  });
  for (const stream of [dedicated.stdout, dedicated.stderr]) {
    stream.on("data", chunk => { dedicatedLog = (dedicatedLog + chunk).slice(-400000); appendFileSync(SERVER_LOG, chunk); });
  }
  await delay(25_000);
  if (dedicated.exitCode !== null || dedicated.signalCode !== null) throw new Error("dedicated server exited early with code " + dedicated.exitCode);

  await client.connect(transport);
  launched.push(1);
  await tool("launch_instance", launchInstanceArgs(1, profileData, [
    ...common, "+set", "uh_cl_LogLevel", "4", "+set", "uh_cl_teaminfo", "1",
    "-port", String(options.gamePort + 1), "+name", "CentaurOptionClient",
  ]), 120_000);
  await delay(10_000);
  await tool("run_command", { instance: 1, text: "connect 127.0.0.1:" + options.gamePort }, 30_000);
  await delay(16_000);
  await tool("run_command", { instance: 1, text: "join" }, 20_000);
  await delay(14_000);
  // Bots keep the round alive and give the probe stable subjects to observe.
  // Driven through the dedicated server's stdin: addbot is a server command.
  const sendServer = async line => {
    if (!dedicated.stdin.writable) throw new Error("dedicated stdin closed");
    dedicated.stdin.write(line + "\n");
    // The engine console input reader must consume one line before the next.
    await delay(300);
  };
  for (let i = 0; i < 4; i++) {
    await sendServer("addbot");
    await delay(1_000);
  }
  await delay(14_000);

  await delay(8000);
  for (let pn=1;pn<5;pn++) await sendServer(`pukename rz_debug_SetPortraitPhase always ${pn} -1`);
  async function capture(label, expected) {
    const actors = [];
    for (let i=0;i<5;i++) {
      const r = await tool("run_command", {instance:1,text:`findactor DLCCentaurOption ${i}`});
      const raw = text(r);
      if (/class DLCCentaurOption\s/.test(raw)) actors.push(raw);
    }
    const counts = [1000,1001].map(tid=>actors.filter(a=>a.includes(`target ${tid} DLCCentaurman`)).length);
    const ok = counts.every((n,i)=>n===expected[i]) && actors.every(a=>/alpha 1\.000000/.test(a) && /state X_4G B/.test(a));
    checks.push({label,ok,counts,actors});
    if (!ok) throw new Error(label+": expected "+expected+", got "+counts);
    return actors;
  }
  // Bot pickups must not contaminate the initial ownership assertion.
  await sendServer("pukename rz_CentaurOptDebug always 1 0 0");
  await sendServer("pukename rz_CentaurOptDebug always 0 1 2");
  await delay(1200);
  await capture("first owner, two slots",[2,0]);
  await sendServer("pukename rz_CentaurOptDebug always 1 4 2");
  await delay(1200);
  await capture("two owners, independent slots",[2,2]);
  for (let mode=1;mode<=5;mode++) {
    await sendServer(`pukename rz_CentaurOptDebug always 0 ${mode} 2`);
    await delay(900);
    const live = await capture("mode "+mode,[2,2]);
    if (mode === 3) {
      const angles = live.filter(a=>a.includes("target 1000 DLCCentaurman")).map(a=>Number(/angle ([\d.]+)/.exec(a)[1])).sort((a,b)=>a-b);
      const ok = Math.abs(angles[0]-240)<0.2 && Math.abs(angles[1]-300)<0.2;
      checks.push({label:"F mode server muzzle angles",ok,angles});
      if (!ok) throw new Error("incorrect client muzzle angles: "+angles);
    }
  }
  await tool("run_command", {instance:1,text:"+altattack"});
  await delay(300);
  const shots = await tool("run_command", {instance:1,text:"findactor DLCCentaurOptionShot 0"});
  await tool("run_command", {instance:1,text:"-altattack"});
  const shotOk = /class DLCCentaurOptionShot\s/.test(text(shots)) && text(shots).includes("target 1000 DLCCentaurman");
  checks.push({label:"network alt-fire projectile",ok:shotOk,output:text(shots)});
  if (!shotOk) throw new Error("option shot did not reach client");
  await tool("run_command", {instance:1,text:"+forward"});
  await delay(1000);
  await tool("run_command", {instance:1,text:"-forward"});
  await tool("run_command", {instance:1,text:"chase"});
  await delay(300);
  const shot = await tool("screenshot", {instance:1});
  for(const c of shot.content || []) if(c.type==="image") writeFileSync("/tmp/centaur-option-fixed.png",Buffer.from(c.data,"base64"));
  await sendServer("pukename rz_CentaurOptDebug always 0 5 1");
  await delay(800);
  await capture("reduce owned stack",[1,2]);
  // Remove slot 0, leaving slot 1 to prove either surviving satellite repairs.
  await sendServer("pukename rz_CentaurOptDebug always 0 5 2");
  await delay(700);
  const before = await capture("restore stack",[2,2]);
  const removeTid = /tid (\d+)/.exec(before.find(a=>a.includes("target 1000 DLCCentaurman")))[1];
  await sendServer("setmaparray centopt_tid 0 0");
  await delay(3000);
  const repaired = await capture("repair removed satellite",[2,2]);
  if (repaired.some(a=>a.includes(`tid ${removeTid}\n`))) throw new Error("old satellite was not removed/replaced");
  await sendServer("pukename rz_CentaurOptDebug always 0 0 0");
  await delay(700);
  await capture("clear only first owner",[0,2]);
  await tool("run_command", {instance:1,text:"disconnect"});
  await delay(500);
  await tool("run_command", {instance:1,text:"connect 127.0.0.1:"+options.gamePort});
  await delay(10000);
  await capture("late client snapshot",[0,2]);
  await sendServer("removebots");
  await delay(1000);
  await capture("owner disconnected cleanup",[0,0]);
  result={pass:checks.every(c=>c.ok),checks,centOptLog:dedicatedLog.split(/\r?\n/).filter(x=>x.includes("CentOpt")),screenshot:"/tmp/centaur-option-fixed.png"};
} catch (error) {
  result = { pass: false, checks, error: String(error), serverLogTail: dedicatedLog.split(/\r?\n/).slice(-35) };
} finally {
  for (const instance of launched.reverse()) {
    try { await tool("kill_instance", { instance }, 15_000); } catch { /* best effort */ }
  }
  if (dedicated && dedicated.exitCode === null && dedicated.signalCode === null) {
    dedicated.kill("SIGTERM");
    await Promise.race([new Promise(r => dedicated.once("exit", r)), delay(4_000)]);
    if (dedicated.exitCode === null && dedicated.signalCode === null) dedicated.kill("SIGKILL");
  }
  await client.close().catch(() => {});
  if (isolatedRoot) rmSync(isolatedRoot, { recursive: true, force: true });
}
console.log(options.json ? JSON.stringify(result) : JSON.stringify(result, null, 2));
process.exit(result.pass ? 0 : 1);
