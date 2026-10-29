#!/usr/bin/env node
//
// Boss stage portrait regression: dedicated server + remote client, stable HP,
// independent variants, reset, reconnect, and controlled dead/slot reuse checks.
// Usage: node tools/mcp/boss-phase-test.mjs [--profile NAME] [--json]
// Env: ZANDRONUM_MCP_DIR, ZANDRONUM_EXE, ZANDRONUM_LAUNCH_PROFILES.

import { spawn } from "node:child_process";
import { appendFileSync, cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { launchInstanceArgs, loadResolvedProfile } from "../resolve-launch-profile.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const PROFILES = resolve(ROOT, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const MCP_DIR = process.env.ZANDRONUM_MCP_DIR;
const ENGINE = process.env.ZANDRONUM_EXE;
const SERVER = process.env.ZANDRONUM_MCP_SERVER || (MCP_DIR ? join(MCP_DIR, "dist/server.js") : "");
const RUNNER = join(ROOT, "tools/mcp/server-runner.mjs");
const SDK = join(MCP_DIR || "", "node_modules/@modelcontextprotocol/sdk/dist/esm");
const SERVER_LOG = "/tmp/boss-phase-server.log";
const SLOTS = 8;

const options = { profile: "mm8bdm-v6c-smoke", gamePort: 10767, bridgePort: Number(process.env.ZANDRONUM_BRIDGE_PORT || 7777), json: false };
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
const CLIENT_LOG = join(dirname(ENGINE || "."), `mcp-bridge-${options.bridgePort}.log`);
for (const path of [SERVER, ENGINE, PROFILES, RUNNER, SDK]) if (!path || !existsSync(path)) {
  console.error("set ZANDRONUM_MCP_DIR / ZANDRONUM_EXE; missing: " + path);
  process.exit(2);
}

function usage() {
  return "Usage: boss-phase-test.mjs [--profile NAME] [--game-port N] [--bridge-port N] [--json]\n" +
    "Force TimemanC and KFC on a dedicated server and verify stage portraits on a remote client.\n" +
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

const client = new Client({ name: "unholy-boss-phase", version: "1.0.0" });
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
async function mapArray(name, index) {
  try {
    const r = await tool("get_map_array", { instance: 1, name, index }, 8_000);
    return r.structuredContent?.value ?? Number(text(r));
  } catch { return null; }
}

let result;
try {
  const { profile: profileData } = loadResolvedProfile(ROOT, PROFILES, options.profile);

  // Dedicated -lastmanstanding server (the round actually starts, so roles and
  // the status snapshot are pushed to the remote client).
  // Isolated engine folder: the dedicated server must not share runtime/config
  // files with the MCP-controlled client.
  isolatedRoot = mkdtempSync(join(tmpdir(), "unholy-boss-phase-"));
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
    "+set", "uh_sv_forcedboss1", "91", "+set", "uh_sv_forcedboss2", "69",
    "+set", "uh_sv_forcebossplayer1", "1", "+set", "uh_sv_forcebossplayer2", "2",
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
    "-port", String(options.gamePort + 1), "+name", "TPClient",
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

  // The round must actually start before playerlifestatusarr is filled in, so
  // poll for ANY assigned role instead of guessing a fixed delay.
  const pollRoles = async () => {
    const out = [];
    for (let k = 0; k < SLOTS; k += 1) out.push(await mapArray("uhtirole", k));
    return out;
  };
  let roles = await pollRoles();
  for (let i = 0; i < 40 && !roles.some(r => r !== null && r >= 0); i += 1) {
    await delay(4_000);
    roles = await pollRoles();
  }
  if (!roles.some(r => r !== null && r >= 0)) throw new Error("round did not start");
  await delay(6_000);


  for (let pn = 0; pn < 5; pn++) {
    await sendServer(`pukename rz_debug_SetPortraitPhase always ${pn} -1`);
  }
  await delay(2_000);
  await tool("run_script", { instance: 1, script: "rz_debug_BossPhaseCheck", args: [], always: true });
  await delay(1_000);

  const checks = [];
  const capture = async (label, expected) => {
    for (const pn of [1, 2]) {
      await tool("run_script", { instance: 1, script: "uh_ti_PhaseCacheDump", args: [pn], always: true });
    }
    await delay(1_500);
    const log = readFileSync(CLIENT_LOG, "utf8");
    const lines = [...log.matchAll(/PhaseCache: slot=(\d+) actor=(\S*) phase=(\d+) portrait=(\S*) icon=(\S*) bossmug=(\S*)/g)];
    const stage = await Promise.all([mapArray("uhtiphase", 1), mapArray("uhtiphase", 2)]);
    const bhw = await Promise.all([mapArray("bhwclientphase", 1), mapArray("bhwclientphase", 2)]);
    const faces = [1, 2].map(pn => lines.filter(x => Number(x[1]) === pn).at(-1)?.slice(1));
    const want = [expected[0] ? "UB091MPG" : "UB091MUG", expected[1] ? "UB069MPG" : "UB069MUG"];
    const ok = stage.every((p, i) => p === expected[i]) && bhw.every((p, i) => p === expected[i])
      && faces.every((x, i) => x && x[3] === want[i] && x[4] === want[i]);
    const check = { label, stage, bhw, faces, ok };
    checks.push(check);
    console.error(JSON.stringify(check));
  };
  const setPhase = async (pn, phase) => {
    await sendServer(`pukename rz_debug_SetPortraitPhase always ${pn} ${phase}`);
    await delay(2_500);
  };
  await setPhase(1, 0);
  await setPhase(2, 0);
  await capture("ordinary", [0, 0]);
  await setPhase(1, 1);
  await capture("Timeman phase only", [1, 0]);
  await setPhase(2, 1);
  await capture("both phases", [1, 1]);
  await setPhase(1, 0);
  await capture("Timeman reset, KFC retained", [0, 1]);

  // Actual reconnect as a true spectator: hello must supply the existing phase.
  await tool("run_command", { instance: 1, text: "disconnect" });
  await delay(2_000);
  await tool("run_command", { instance: 1, text: "connect 127.0.0.1:" + options.gamePort });
  await delay(16_000);
  await capture("reconnect snapshot", [0, 1]);

  // Controlled body-less death/slot-reuse receiver checks supplement the
  // production server -> remote client delivery proved above.
  const local = async (script, args) => {
    await tool("run_script", { instance: 1, script, args, always: true });
    await delay(700);
  };
  const angryDeadLine = "PhaseCache: slot=63 actor=TimemanC phase=1 portrait=UB091MPG icon=UB091MPG bossmug=PFACE91";
  await local("uh_ti_sync_status", [63, 2, 2, 91]);
  await local("uh_ti_sync_phase", [63, 2, 91, 1]);
  await local("uh_ti_sync_status", [63, 0, 2, 91]);
  await local("uh_ti_PhaseCacheDump", [63]);
  let log = readFileSync(CLIENT_LOG, "utf8");
  const dead = log.includes(angryDeadLine);
  await local("uh_ti_sync_status", [63, 2, 2, 69]);
  await local("uh_ti_sync_phase", [63, 2, 69, 0]);
  await local("uh_ti_PhaseCacheDump", [63]);
  log = readFileSync(CLIENT_LOG, "utf8");
  const reused = log.includes("PhaseCache: slot=63 actor=KFCDragon756 phase=0 portrait=UB069MUG icon=UB069MUG bossmug=");
  await local("uh_ti_sync_status", [63, -1, 0, 0]);
  const cleared = await mapArray("uhtiphase", 63) === 0;

  // Queued ACS scripts can run in reverse packet order within the same tic.
  await local("uh_ti_sync_phase", [63, 2, 91, 1]);
  await local("uh_ti_sync_status", [63, 2, 2, 91]);
  await local("uh_ti_PhaseCacheDump", [63]);
  log = readFileSync(CLIENT_LOG, "utf8");
  const reverseOrder = await mapArray("uhtiphase", 63) === 1 && log.includes(angryDeadLine);
  await local("uh_ti_sync_status", [63, -1, 0, 0]);

  // Player-context logging can appear in either server or client output.
  const flagLines = [...(dedicatedLog + "\n" + log).matchAll(/BossPhaseSet: slot=(\d+) actor=(\S+) phase=(\d+) hp=(\d+)/g)]
    .map(m => m.slice(1));
  const stableHealth = [1, 2].every(pn => {
    const health = flagLines.filter(m => Number(m[0]) === pn).map(m => m[3]);
    return health.length >= 3 && new Set(health).size === 1;
  });
  const tableOk = log.includes("BossPhaseCheck: failures=0");
  result = {
    checks, dead, reused, cleared, reverseOrder, stableHealth, tableOk, flagLines,
    pass: checks.every(c => c.ok) && dead && reused && cleared && reverseOrder && stableHealth && tableOk,
  };
} catch (error) {
  result = { pass: false, error: String(error), serverLogTail: dedicatedLog.split(/\r?\n/).slice(-35) };
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
