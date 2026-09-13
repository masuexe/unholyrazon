#!/usr/bin/env node

// Directed versus-combo 207 network probe.
//
// Brings up one dedicated `-lastmanstanding` server plus two clients (one
// bridge-controlled, one directly observed), adds bots so 207's four-player
// minimum is met, forces `uh_sv_BossEventNum 207`, then verifies on the live
// client that the two versus bosses exist and that neither carries
// `PowerProtectBoss`.  That is the network-side counterpart to the local
// uh_BossMorph probe: without the versus exemption the bosses would be immune
// to each other and no real projectile could ever decide the duel.
//
// This is a focused smoke probe, not a replacement for the manual gameplay
// gate (real projectiles, single-death result, disconnect handling).

import { spawn } from "node:child_process";
import { appendFileSync, cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { launchInstanceArgs, loadResolvedProfile } from "../resolve-launch-profile.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const PROFILES = process.env.ZANDRONUM_LAUNCH_PROFILES || join(ROOT, "tools/mm8bdm-v6b-linux.launch.json");
const RUNNER = join(ROOT, "tools/mcp/server-runner.mjs");

function usage() {
  return `Usage: versus-207-test.mjs [--profile NAME] [--game-port N] [--combo N] [--expect A,B] [--json] [--dry-run]

Launch a dedicated LMS server and two clients, force a versus boss combo, and
verify that its two bosses spawn without PowerProtectBoss.  Defaults to combo
207 (Red Baron / Blue Jay).
`;
}

const options = { profile: "mm8bdm-v6b-smoke", port: 10760, combo: 207, expect: ["RedBaronDuo", "BlueJayDuo"], forced1: null, forced2: null, resolveWait: 30000, json: false, dryRun: false };
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === "--help" || arg === "-h") { console.log(usage()); process.exit(0); }
  if (arg === "--json") { options.json = true; continue; }
  if (arg === "--dry-run") { options.dryRun = true; continue; }
  if (arg === "--profile") { options.profile = process.argv[++i] || ""; continue; }
  if (arg === "--game-port") { options.port = Number.parseInt(process.argv[++i], 10); continue; }
  if (arg === "--combo") { options.combo = Number.parseInt(process.argv[++i], 10); continue; }
  if (arg === "--expect") { options.expect = (process.argv[++i] || "").split(",").map(s => s.trim()).filter(Boolean); continue; }
  if (arg === "--resolve-wait") { options.resolveWait = Number.parseInt(process.argv[++i], 10); continue; }
  if (arg === "--forced1") { options.forced1 = Number.parseInt(process.argv[++i], 10); continue; }
  if (arg === "--forced2") { options.forced2 = Number.parseInt(process.argv[++i], 10); continue; }
  throw new Error(`unknown option ${arg}`);
}
if (!options.profile || !Number.isInteger(options.port) || options.port < 1024 || options.port > 65535) throw new Error("invalid options");
if (!Number.isInteger(options.combo) || options.combo < 0) throw new Error("invalid combo");
if (options.expect.length !== 2 && !(options.expect.length === 1 && (options.expect[0] === "any" || options.expect[0] === "*"))) throw new Error("--expect needs two class names (or 'any')");
const MCP_DIR = process.env.ZANDRONUM_MCP_DIR;
if (!MCP_DIR) throw new Error("set ZANDRONUM_MCP_DIR to your ZandronumMCP checkout");
const SERVER = process.env.ZANDRONUM_MCP_SERVER || join(MCP_DIR, "dist/server.js");
const ENGINE = process.env.ZANDRONUM_EXE;
if (!ENGINE) throw new Error("set ZANDRONUM_EXE to the bridge-patched Zandronum binary");
const SDK = join(MCP_DIR, "node_modules/@modelcontextprotocol/sdk/dist/esm");
for (const path of [SERVER, ENGINE, PROFILES, RUNNER]) if (!existsSync(path)) throw new Error(`missing path: ${path}`);
if (options.dryRun) {
  console.log(JSON.stringify({ status: "dry-run", profile: options.profile, gamePort: options.port, server: SERVER, engine: ENGINE }));
  process.exit(0);
}

const [{ Client }, { StdioClientTransport }] = await Promise.all([
  import(pathToFileURL(join(SDK, "client/index.js"))),
  import(pathToFileURL(join(SDK, "client/stdio.js"))),
]);
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [RUNNER, SERVER],
  cwd: MCP_DIR,
  env: { ...process.env, ZANDRONUM_EXE: ENGINE, ZANDRONUM_LAUNCH_PROFILES: PROFILES, ZANDRONUM_BRIDGE_PORT: "7777" },
  stderr: "pipe",
});
let stderr = "";
transport.stderr?.on("data", chunk => { stderr = `${stderr}${chunk}`.slice(-12000); });
const client = new Client({ name: "unholy-versus-207-test", version: "1.0.0" });
const launched = [];
let dedicated;
let dedicatedLog = "";
let directClient;
let directClientLog = "";
let isolatedRoot;
const text = result => (result.content || []).filter(x => x.type === "text").map(x => x.text).join("\n");
async function tool(name, args, timeout = 90_000) {
  const result = await client.callTool({ name, arguments: args }, undefined, { timeout });
  if (result.isError) throw new Error(`${name}: ${text(result)}`);
  return result;
}
const sleep = ms => new Promise(resolveDelay => setTimeout(resolveDelay, ms));
const common = ["-nosound", "+set", "vid_renderer", "0", "+set", "fullscreen", "0"];
let result;
try {
  await client.connect(transport);
  const { profile: profileData } = loadResolvedProfile(ROOT, PROFILES, options.profile);

  // Bridge-controlled client first (see network-test.mjs for why).
  launched.push(1);
  await tool("launch_instance", launchInstanceArgs(1, profileData, [...(profileData.extraArgs || []), ...common, "-port", String(options.port + 1), "+name", "VersusClient1"]));

  isolatedRoot = mkdtempSync(join(tmpdir(), "unholy-versus-"));
  const serverDir = join(isolatedRoot, "server");
  const directDir = join(isolatedRoot, "client2");
  cpSync(dirname(ENGINE), serverDir, { recursive: true });
  cpSync(dirname(ENGINE), directDir, { recursive: true });
  const serverEngine = join(serverDir, "zandronum");
  const directEngine = join(directDir, "zandronum");
  const serverArgs = [
    "-stdout", "-iwad", profileData.iwad, "-file", ...(profileData.files || []),
    "-host", "8", "-port", String(options.port), "-lastmanstanding",
    "+map", profileData.map || "MM2DW1",
    ...common,
    "+set", "sv_cheats", "1",
    "+set", "sv_updatemaster", "0",
    "+set", "sv_noplayertimeout", "1",
    "+set", "uh_sv_BossDebugText", "1",
  ];
  dedicated = spawn(serverEngine, serverArgs, { cwd: serverDir, env: { ...process.env, SDL_VIDEODRIVER: "offscreen", ZANDRONUM_BRIDGE_PORT: String(options.port + 100) }, stdio: ["pipe", "pipe", "pipe"] });
  const serverLogPath = "/tmp/versus-207-server.log";
  writeFileSync(serverLogPath, "");
  for (const stream of [dedicated.stdout, dedicated.stderr]) stream.on("data", chunk => { dedicatedLog = `${dedicatedLog}${chunk}`.slice(-400000); appendFileSync(serverLogPath, chunk); });
  console.error(`[versus-207] server log -> ${serverLogPath}`);
  await sleep(20_000);
  if (dedicated.exitCode !== null) throw new Error(`dedicated server exited early with code ${dedicated.exitCode}`);

  const connected = await tool("run_command", { instance: 1, text: `connect 127.0.0.1:${options.port}` }, 15_000);
  const connectOutputs = [text(connected)];
  let firstClientLog = "";
  for (let attempt = 0; attempt < 30; attempt += 1) {
    firstClientLog = await tool("read_engine_log", { instance: 1, cursor: 0, maxLines: 1000 }, 15_000).then(text);
    if (/Level authenticated![\s\S]*Snapshot received\./i.test(firstClientLog)) break;
    await sleep(2000);
  }
  const firstAuthenticated = /Level authenticated![\s\S]*Snapshot received\./i.test(firstClientLog);
  if (!firstAuthenticated) throw new Error("MCP client did not authenticate within 60 seconds");

  const directArgs = ["-stdout", "-iwad", profileData.iwad, "-file", ...(profileData.files || []), "-port", String(options.port + 2), ...common, "+name", "VersusClient2", "+connect", `127.0.0.1:${options.port}`];
  directClient = spawn(directEngine, directArgs, { cwd: directDir, env: { ...process.env, SDL_VIDEODRIVER: "offscreen", ZANDRONUM_BRIDGE_PORT: String(options.port + 101) }, stdio: ["ignore", "pipe", "pipe"] });
  for (const stream of [directClient.stdout, directClient.stderr]) stream.on("data", chunk => { directClientLog = `${directClientLog}${chunk}`.slice(-400000); });
  await sleep(30_000);

  // Two bots bring the player count to four so MaxBossCountForPlayers >= 2.
  // I_ConsoleInput reads a whole chunk from stdin, so the commands must be
  // separated in time or they are parsed as one line (`addbot addbot`).
  for (let bot = 1; bot <= 4; bot += 1) {
    dedicated.stdin.write("addbot\n");
    console.error(`[versus-207] addbot ${bot}`);
    await sleep(2500);
  }
  await sleep(8000);
  // Force the selection explicitly: the OPEN countdown script only selects
  // bosses when it observes GAMESTATE_INPROGRESS, which depends on when the
  // second player finishes connecting.
  dedicated.stdin.write(`uh_sv_BossEventNum ${options.combo}\n`);
  await sleep(1500);
  if (Number.isInteger(options.forced1)) { dedicated.stdin.write(`uh_sv_ForcedBoss1 ${options.forced1}\n`); await sleep(1000); }
  if (Number.isInteger(options.forced2)) { dedicated.stdin.write(`uh_sv_ForcedBoss2 ${options.forced2}\n`); await sleep(1000); }
  dedicated.stdin.write("puke ub_SelectBossAndEvent\n");
  console.error("[versus-207] server puke ub_SelectBossAndEvent");

  // Wait for the forced combo's selection to reach the authoritative server
  // log (its stdout is buffered), then read the two boss TIDs from it.  Anchor
  // on the forced CVAR line so an earlier automatic two-boss round is ignored.
  let selectionText = "";
  for (let attempt = 0; attempt < 240 && !selectionText; attempt += 1) {
    const logText = existsSync(serverLogPath) ? readFileSync(serverLogPath, "utf8") : dedicatedLog;
    const idx = logText.lastIndexOf(`uh_sv_BossEventNum' was '${options.combo}'`);
    if (idx >= 0) {
      const tail = logText.slice(idx);
      if (/Boss 1 TID = \d+[\s\S]*?Boss 2 TID = \d+/.test(tail)) selectionText = tail;
    }
    if (!selectionText) await sleep(500);
  }
  const tidMatch = selectionText.match(/Boss 1 TID = (\d+)[\s\S]*?Boss 2 TID = (\d+)/);
  const resolvedMatch = selectionText.match(new RegExp(`Boss combo ${options.combo} resolved: (-?\\d+) vs (-?\\d+)`));
  const lastTids = tidMatch ? [Number(tidMatch[1]), Number(tidMatch[2])] : [];
  const resolvedIds = resolvedMatch ? [Number(resolvedMatch[1]), Number(resolvedMatch[2])] : [];
  const bossStates = [];
  for (const tid of lastTids) {
    try {
      const stateResult = await tool("actor_state", { instance: 1, tid }, 15_000);
      const state = stateResult.structuredContent || JSON.parse(text(stateResult));
      const inventory = Array.isArray(state.inventory) ? state.inventory : [];
      bossStates.push({
        className: state.class,
        tid,
        hasPowerProtectBoss: inventory.some(item => item.class === "PowerProtectBoss"),
        health: state.health,
      });
    } catch (error) {
      bossStates.push({ tid, error: error instanceof Error ? error.message : String(error) });
    }
  }
  await sleep(options.resolveWait);
  // The versus round resolved if the log shows any ending after the forced
  // combo's CVAR line: the engine's LMS winner/win limit, a map change, or the
  // next round's selection.  A soft-locked watcher would show none of these.
  const finalLog = existsSync(serverLogPath) ? readFileSync(serverLogPath, "utf8") : dedicatedLog;
  const anchorIdx = finalLog.lastIndexOf(`uh_sv_BossEventNum' was '${options.combo}'`);
  const afterVs = anchorIdx >= 0 ? finalLog.slice(anchorIdx) : "";
  const versusResolved = /multiBossCheck|Winlimit hit|ACS scripts unloaded|wins!/i.test(afterVs);

  const log = dedicatedLog;
  const names = ["VersusClient1", "VersusClient2"];
  const missing = names.filter(name => !log.includes(name));
  const expectAny = options.expect.length === 1 && (options.expect[0] === "any" || options.expect[0] === "*");
  let bothBossesSpawned;
  if (expectAny) {
    bothBossesSpawned = bossStates.length === 2 && bossStates.every(entry => !entry.error && entry.className);
  } else {
    const classes = bossStates.map(entry => entry.className).sort();
    const expected = [...options.expect].sort();
    bothBossesSpawned = classes.length === 2 && classes[0] === expected[0] && classes[1] === expected[1] && bossStates.every(entry => !entry.error);
  }
  const noProtection = bossStates.length === 2 && bossStates.every(entry => entry.hasPowerProtectBoss === false);
  let clientVars = {};
  for (const name of ["multibosscheck", "versusfightevent", "activebosscombo", "isbosseventactive"]) {
    try {
      const state = await tool("get_map_var", { instance: 1, name }, 10_000);
      clientVars[name] = state.structuredContent || text(state);
    } catch (error) {
      clientVars[name] = `error: ${error instanceof Error ? error.message : String(error)}`;
    }
  }
  result = {
    status: missing.length === 0 && bothBossesSpawned && noProtection && versusResolved ? "pass" : "fail",
    profile: options.profile,
    gamePort: options.port,
    combo: options.combo,
    expectedClasses: options.expect,
    resolvedIds,
    connectedNames: names.filter(n => !missing.includes(n)),
    missingNames: missing,
    connectOutputs,
    bossStates,
    bothBossesSpawned,
    noProtection,
    versusResolved,
    clientVars,
    serverMarkers: log.split(/\r?\n/).filter(line => /Unholy|Boss combo|UnholyBoss|Morphed|multiBoss|entered the game|Invalid bot|Bots cannot|Only the host/i.test(line)).slice(-40),
    serverLogTail: log.split(/\r?\n/).slice(-60),
    directClientAuthenticated: /Connected![\s\S]*Level authenticated![\s\S]*Snapshot received\./i.test(directClientLog),
  };
} catch (error) {
  result = { status: "error", error: error instanceof Error ? error.message : String(error), serverStderr: stderr, serverLogTail: dedicatedLog.split(/\r?\n/).slice(-60) };
} finally {
  for (const instance of launched.reverse()) {
    try { await tool("kill_instance", { instance }, 15_000); } catch { /* cleanup best effort */ }
  }
  if (dedicated?.exitCode === null) {
    dedicated.kill("SIGTERM");
    await Promise.race([new Promise(resolveExit => dedicated.once("exit", resolveExit)), sleep(3000)]);
    if (dedicated.exitCode === null) dedicated.kill("SIGKILL");
  }
  if (directClient?.exitCode === null) {
    directClient.kill("SIGTERM");
    await Promise.race([new Promise(resolveExit => directClient.once("exit", resolveExit)), sleep(3000)]);
    if (directClient.exitCode === null) directClient.kill("SIGKILL");
  }
  await client.close();
  if (isolatedRoot) rmSync(isolatedRoot, { recursive: true, force: true });
}
console.log(options.json ? JSON.stringify(result) : JSON.stringify(result, null, 2));
process.exitCode = result.status === "pass" ? 0 : 1;
