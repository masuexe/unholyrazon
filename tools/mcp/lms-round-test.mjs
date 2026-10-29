#!/usr/bin/env node
//
// lms-round-test.mjs - runtime scenario gate for one complete Unholy LMS round.
//
// STATUS: NOT A GATE CHECK YET - do not register it in tools/gate.py until it
// exits 0.  Last recorded v6c run (2026-10-29, after adding a bounded ready
// weapon wait and sv_limitcommands 0): 12 of 16 assertions passed.  The three
// stable failures are (1) morphed bosses and (2) rz_debug_MorphMe carry
// MorphedFlag but `actor_state` still reports no ready weapon after a 15 s
// window, and (3) the clean `disconnect` logs "0 has disconnected!!" yet
// playerlifestatusarr[clientSlot] stays 1.  After that disconnect the server
// shows uh_settlementstate[1] = 1 and totalplayersarr[PLS_BOSS] = 0, so the
// "round survives the disconnect" wait times out; the survivor bots may simply
// lose the 2v2 during the 60 s window.  The command-flood ban is gone.
// Next session: decide whether a bot boss is expected to hold a ReadyWeapon at
// all (check a real client boss), make the disconnect markers read immediately
// after the leave, and reconcile the DISCONNECT handler with the observed role.
// Then get one green run and append to gate.py (group "full", kind "engine",
// requires ["node","zandronum"], timeout 900).
//
// Why the static layer cannot prove this: every other check in tools/ either
// reads source or runs ACS under C stubs.  None of them can show that the round
// really starts on a server, that the selected player really becomes the boss
// ACTOR, that a remote client sees that morph, that the settlement watcher
// enters its cancellable exit window, or that uh_sv_resumeonrevive cancels that
// window when a revived opponent returns.  Those are engine scheduling, morph,
// HUD delivery and network-replication behaviours, so this test drives them:
// one dedicated -lastmanstanding server, one MCP-controlled client, bots, and a
// second MCP instance attached to the authoritative server itself.
//
// Why two bosses: the engine ends a native LMS round as soon as only one
// living/respawnable player remains (lastmanstanding.cpp).  A single-boss round
// therefore commits its native result the moment the survivor side empties, and
// the mod's cancellable window is never reached.  With two bosses alive the
// survivor side can empty without triggering that native win, which is exactly
// the ordinary-round settlement path the option governs.
//
// Phases (each assertion row is independent evidence):
//   1. round start   - living client pawn, authoritative survivor role, two
//                      bosses, no result window, boss HUD / role snapshot on
//                      the remote client.
//   2. boss morph    - the forced boss actor class and boss inventory on the
//                      server and on the remote client, plus rz_debug_MorphMe
//                      class change and restore on a real player.
//   3. settlement    - killing every survivor enters the cancellable window
//                      (gameover stays false, deadline in the future) and a
//                      real Dickhead revival cancels it (pending cleared,
//                      living survivor again, round still in progress).
//   4. reconnect     - the client leaves mid-round and rejoins the ongoing map
//                      with its authoritative role and round state intact.
//   5. teardown      - the client instance quits cleanly, the server exits on
//                      request, and no engine process is left behind.
//
// Usage:
//   node tools/mcp/lms-round-test.mjs [--profile NAME] [--game-port N]
//        [--json] [--dry-run] [--keep-logs]
//
// Env overrides (same family as the other tools/mcp scripts):
//   ZANDRONUM_MCP_DIR, ZANDRONUM_MCP_SERVER, ZANDRONUM_EXE,
//   ZANDRONUM_LAUNCH_PROFILES, ZANDRONUM_NODE.

import { spawn } from "node:child_process";
import { appendFileSync, cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { launchInstanceArgs, loadResolvedProfile } from "../resolve-launch-profile.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const PROFILES = resolve(ROOT, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const RUNNER = join(ROOT, "tools/mcp/server-runner.mjs");
const CLIENT_INSTANCE = 1;
const MAX_PLAYERS = 64;

// Two forced bosses keep the engine's native single-winner result out
// of the way, so the cancellable ordinary-round settlement is reachable.
const FORCED_BOSSES = [
  { boss: 91, player: 1, actor: "TimemanC" },
  { boss: 69, player: 2, actor: "KFCDragon756" },
];
const SURVIVOR_BOTS = 2; // plus the MCP client = three survivors
const TOTAL_BOTS = FORCED_BOSSES.length + SURVIVOR_BOTS;

// PLS_* from src/acs_source/unholy/uh_def.acs
const PLS_NULL = -1,
  PLS_DEAD = 0,
  PLS_SURVIVOR = 1,
  PLS_BOSS = 2;
// UH_SETTLEMENT_* from uh_def.acs (uh_settlementstate indexes).
const SETTLE_PENDING = 0,
  SETTLE_GENERATION = 1,
  SETTLE_STARTED = 2,
  SETTLE_DEADLINE = 3;

function usage() {
  return [
    "Usage: lms-round-test.mjs [options]",
    "",
    "Drive one complete Unholy LMS round on a dedicated server with one",
    "MCP-controlled client and bots, and assert the observable engine state of",
    "every phase: round start, boss morph, cancellable settlement, revival",
    "cancellation, mid-round reconnect and clean teardown.",
    "",
    "Options:",
    "  --profile NAME     launch profile (default: mm8bdm-v6c-smoke)",
    "  --game-port N      server UDP/TCP port (default: 10890)",
    "  --json             emit one machine-readable JSON object",
    "  --dry-run          validate paths and print the resolved configuration",
    "  --keep-logs        keep the isolated engine folder and print its path",
    "  --help             show this help",
    "",
    "Environment overrides:",
    "  ZANDRONUM_NODE, ZANDRONUM_MCP_DIR, ZANDRONUM_MCP_SERVER,",
    "  ZANDRONUM_EXE, ZANDRONUM_LAUNCH_PROFILES",
  ].join("\n");
}

function parsePositiveInt(value, flag) {
  const n = Number.parseInt(value, 10);
  if (!Number.isInteger(n) || n <= 0) throw new Error(flag + " expects a positive integer");
  return n;
}

const options = { profile: "mm8bdm-v6c-smoke", gamePort: 10890, json: false, dryRun: false, keepLogs: false };
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === "--help" || arg === "-h") { console.log(usage()); process.exit(0); }
  if (arg === "--json") { options.json = true; continue; }
  if (arg === "--dry-run") { options.dryRun = true; continue; }
  if (arg === "--keep-logs") { options.keepLogs = true; continue; }
  if (arg === "--profile") { options.profile = process.argv[++i] || ""; continue; }
  if (arg === "--game-port") { options.gamePort = parsePositiveInt(process.argv[++i], "--game-port"); continue; }
  throw new Error("unknown option " + arg + " (use --help)");
}
if (!options.profile) throw new Error("invalid --profile");
if (options.gamePort < 1024 || options.gamePort > 64000) throw new Error("invalid --game-port");

const MCP_DIR = process.env.ZANDRONUM_MCP_DIR;
if (!MCP_DIR) throw new Error("set ZANDRONUM_MCP_DIR to your ZandronumMCP checkout");
const SERVER = process.env.ZANDRONUM_MCP_SERVER || join(MCP_DIR, "dist/server.js");
const ENGINE = process.env.ZANDRONUM_EXE;
if (!ENGINE) throw new Error("set ZANDRONUM_EXE to the bridge-patched Zandronum binary");
const SDK = join(MCP_DIR, "node_modules/@modelcontextprotocol/sdk/dist/esm");
for (const path of [SERVER, ENGINE, PROFILES, RUNNER]) {
  if (!existsSync(path)) throw new Error("missing path: " + path);
}

// The dedicated server and the MCP-controlled client need separate bridge
// ports: the MCP session base port belongs to the client, and the server is
// driven separately from its own console (see serverOutput below).
const SERVER_BRIDGE_PORT = options.gamePort + 100;
const CLIENT_BRIDGE_PORT = options.gamePort + 200;

if (options.dryRun) {
  const { profile, files } = loadResolvedProfile(ROOT, PROFILES, options.profile);
  console.log(JSON.stringify({
    status: "dry-run",
    profile: options.profile,
    gamePort: options.gamePort,
    serverBridgePort: SERVER_BRIDGE_PORT,
    clientBridgePort: CLIENT_BRIDGE_PORT,
    server: SERVER,
    engine: ENGINE,
    map: profile.map,
    files,
    forcedBosses: FORCED_BOSSES,
    bots: TOTAL_BOTS,
  }));
  process.exit(0);
}

const [{ Client }, { StdioClientTransport }] = await Promise.all([
  import(pathToFileURL(join(SDK, "client/index.js"))),
  import(pathToFileURL(join(SDK, "client/stdio.js"))),
]);

const transport = new StdioClientTransport({
  command: process.env.ZANDRONUM_NODE || process.execPath,
  args: [RUNNER, SERVER],
  cwd: MCP_DIR,
  env: {
    ...process.env,
    // The MCP-launched client must be able to initialize video without an X
    // display: the gate runs in headless shells, and SDL's offscreen driver is
    // what the dedicated-server checks already use. Without it the engine quits
    // during video init and the bridge port never opens.
    SDL_VIDEODRIVER: process.env.SDL_VIDEODRIVER || "offscreen",
    ZANDRONUM_EXE: ENGINE,
    ZANDRONUM_LAUNCH_PROFILES: PROFILES,
    ZANDRONUM_BRIDGE_PORT: String(CLIENT_BRIDGE_PORT),
  },
  stderr: "pipe",
});
let serverStderr = "";
transport.stderr?.on("data", (chunk) => { serverStderr = (serverStderr + chunk).slice(-12000); });

const client = new Client({ name: "unholy-lms-round", version: "1.0.0" });
const startedAt = Date.now();
const delay = (ms) => new Promise((r) => setTimeout(r, ms));
const launched = [];
let dedicated;
let dedicatedLog = "";
let isolatedRoot;
let serverLogPath;
const cleanup = {};

const text = (result) => (result.content || []).filter((x) => x.type === "text").map((x) => x.text).join("\n");

async function tool(name, args, timeout = 60_000) {
  const result = await client.callTool({ name, arguments: args }, undefined, { timeout });
  if (result.isError) throw new Error(name + ": " + text(result));
  return result;
}
const clientTool = (name, args = {}, timeout) => tool(name, { instance: CLIENT_INSTANCE, ...args }, timeout);

// The dedicated server is driven through its own stdin and its console output
// is read back from the engine log: bridge tool calls cannot correlate a reply
// on a dedicated server (they print to stdout, but the bridge sentinel never
// returns), so every authoritative read is a console command plus a log parse.
async function clientMapVar(name) {
  const result = await tool("get_map_var", { instance: CLIENT_INSTANCE, name }, 10_000);
  return result.structuredContent ? result.structuredContent.value : Number(text(result));
}
async function tryClientMapVar(name) {
  try { return await clientMapVar(name); } catch { return null; }
}
async function clientMapArray(name, index) {
  const result = await tool("get_map_array", { instance: CLIENT_INSTANCE, name, index }, 10_000);
  return result.structuredContent ? result.structuredContent.value : Number(text(result));
}
async function tryClientMapArray(name, index) {
  try { return await clientMapArray(name, index); } catch { return null; }
}

const BLOCK_SENTINEL = "__LMS_BLOCK_DONE__";

/** Send one console command, then return the console output it produced. */
async function serverOutput(command, timeoutMs = 15_000) {
  const start = readServerLog().length;
  sendServer(command + "; echo " + BLOCK_SENTINEL);
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    await delay(100);
    if (dedicated && (dedicated.exitCode !== null || dedicated.signalCode !== null)) {
      throw new Error("dedicated server exited while running: " + command);
    }
    const out = readServerLog().slice(start);
    const end = out.indexOf(BLOCK_SENTINEL);
    if (end >= 0) return out.slice(0, end);
  }
  throw new Error("server console response timed out for: " + command);
}

/** Read one map variable from the authoritative server. */
async function srvMapVar(name) {
  const out = await serverOutput("getmapvar " + name);
  const match = out.match(new RegExp("mapvar " + name + " = (-?\\d+)"));
  if (!match) throw new Error("getmapvar " + name + " produced no value: " + out.trim().slice(-200));
  return Number(match[1]);
}
async function trySrvMapVar(name) {
  try { return await srvMapVar(name); } catch { return null; }
}
async function srvMapArray(name, index) {
  const out = await serverOutput("getmaparray " + name + " " + index);
  const match = out.match(new RegExp("maparray " + name + "\\[" + index + "\\] = (-?\\d+)"));
  if (!match) throw new Error("getmaparray " + name + "[" + index + "] produced no value");
  return Number(match[1]);
}
async function trySrvMapArray(name, index) {
  try { return await srvMapArray(name, index); } catch { return null; }
}

/** Authoritative actor state from the server console (`dumpactor`). */
async function srvActorState(tid) {
  const out = await serverOutput("dumpactor " + tid);
  if (!/MCP_ACTOR/.test(out)) return null;
  const cls = out.match(/^class (\S+)$/m);
  const health = out.match(/^health (-?\d+)$/m);
  if (!cls) return null;
  const inventory = [];
  for (const line of out.split(/\r?\n/)) {
    const item = line.match(/^item (\S+) /);
    if (item) inventory.push({ class: item[1] });
  }
  return { tid, class: cls[1], health: health ? Number(health[1]) : null, inventory };
}
async function trySrvActorState(tid) {
  try { return await srvActorState(tid); } catch { return null; }
}

async function actorState(instance, tid) {
  const args = tid === undefined ? {} : { tid };
  const result = await tool("actor_state", { instance, ...args }, 15_000);
  return result.structuredContent || JSON.parse(text(result));
}
async function tryActorState(instance, tid) {
  try {
    const state = await actorState(instance, tid);
    return state && state.class ? state : null;
  } catch { return null; }
}
function hasInventory(state, className) {
  const inventory = Array.isArray(state && state.inventory) ? state.inventory : [];
  return inventory.some((item) => String(item.class || "").toLowerCase() === className.toLowerCase());
}
function hudMessages(result) {
  const structured = (result && result.structuredContent) || {};
  const messages = Array.isArray(structured.messages) ? structured.messages : [];
  return messages.map((message) => ({
    id: message.id,
    text: String(message.text === undefined ? "" : message.text),
    layer: message.layer,
    tics: message.tics,
  }));
}

async function waitFor(label, fn, timeoutMs = 120_000, intervalMs = 250) {
  const deadline = Date.now() + timeoutMs;
  let last;
  while (Date.now() < deadline) {
    try {
      last = await fn();
      if (last) return last;
    } catch (error) {
      last = { error: error instanceof Error ? error.message : String(error) };
    }
    await delay(intervalMs);
  }
  throw new Error(label + " timed out after " + timeoutMs + "ms (last: " + JSON.stringify(last) + ")");
}

const assertions = [];
function check(name, pass, detail) {
  assertions.push({ name, pass: !!pass, detail });
  if (!options.json) {
    console.error("[" + (pass ? "PASS" : "FAIL") + "] " + name + (detail === undefined ? "" : " :: " + JSON.stringify(detail)));
  }
  return !!pass;
}

function sendServer(line) {
  if (!dedicated || !dedicated.stdin || !dedicated.stdin.writable) throw new Error("dedicated stdin is not writable");
  dedicated.stdin.write(line + "\n");
}
async function serverCommand(line, settleMs = 400) {
  // The dedicated console input reader consumes one line per poll, so console
  // commands must be paced instead of written back to back.
  sendServer(line);
  await delay(settleMs);
}
function readServerLog() {
  try { return readFileSync(serverLogPath, "utf8"); } catch { return dedicatedLog; }
}

async function portIsFree(port) {
  const net = await import("node:net");
  return new Promise((resolvePromise) => {
    const socket = net.connect({ host: "127.0.0.1", port });
    socket.setTimeout(1500);
    socket.once("connect", () => { socket.destroy(); resolvePromise(false); });
    socket.once("timeout", () => { socket.destroy(); resolvePromise(true); });
    socket.once("error", () => { socket.destroy(); resolvePromise(true); });
  });
}

// Idempotent teardown: the phase-5 checks call it explicitly, and the finally
// block calls it again so a failed assertion can never leave an engine behind.
let teardownDone = false;
async function teardownEngines() {
  if (teardownDone) return;
  teardownDone = true;
  for (const instance of launched.slice().reverse()) {
    try {
      cleanup.client = text(await tool("kill_instance", { instance }, 25_000));
    } catch (error) {
      cleanup.client = "failed: " + (error instanceof Error ? error.message : String(error));
    }
  }
  // The dedicated server is stopped through its own console: a bridge command
  // that ends the process can never answer the sentinel it was given.
  try { sendServer("quit"); } catch { /* stdin may already be closed */ }
  await Promise.race([
    new Promise((r) => { if (dedicated) dedicated.once("exit", r); else r(); }),
    delay(10_000),
  ]);
  if (dedicated && dedicated.exitCode === null && dedicated.signalCode === null) {
    cleanup.serverForced = true;
    dedicated.kill("SIGTERM");
    await Promise.race([new Promise((r) => dedicated.once("exit", r)), delay(4000)]);
  }
  if (dedicated && dedicated.exitCode === null && dedicated.signalCode === null) dedicated.kill("SIGKILL");
  await delay(300);
  cleanup.serverExited = !!dedicated && (dedicated.exitCode !== null || dedicated.signalCode !== null);
  try { await client.close(); } catch { /* already closed */ }
}

// Connect the MCP client and join it to the running round. The client engine
// log is not usable as proof here: the bridge writes it next to the engine
// binary, which can be a read-only install, so `read_engine_log` may fail. The
// authoritative server proves the join instead: after the client joins, slot 0
// owns a real pawn there, and its class must match what the client sees.
async function joinOngoingRound() {
  const logStart = readServerLog().length;
  await clientTool("run_command", { text: "connect 127.0.0.1:" + options.gamePort }, 30_000);
  await clientTool("set_pause", { paused: false }, 10_000).catch(() => null);
  await waitFor("server accepts the client", async () => {
    const out = readServerLog().slice(logStart);
    return /LMSClient[^\n]*(has connected|entered the game)/i.test(out) ? out : null;
  }, 120_000, 500);
  return waitFor("client join", async () => {
    await clientTool("run_command", { text: "join" }, 20_000).catch(() => null);
    await delay(400);
    const local = await tryActorState(CLIENT_INSTANCE);
    if (!local || Number(local.health) <= 0) return null;
    const serverSide = await trySrvActorState(Number(local.tid));
    return serverSide && serverSide.class === local.class ? { local, serverSide } : null;
  }, 180_000, 3_000);
}

let result;
try {
  const { profile: profileData } = loadResolvedProfile(ROOT, PROFILES, options.profile);
  const map = profileData.map || "MM2DW1";


  isolatedRoot = mkdtempSync(join(tmpdir(), "unholy-lms-round-"));
  const serverDir = join(isolatedRoot, "server");
  cpSync(dirname(ENGINE), serverDir, { recursive: true });
  serverLogPath = join(isolatedRoot, "server.log");
  writeFileSync(serverLogPath, "");

  const common = ["-nosound", "+set", "vid_renderer", "0", "+set", "fullscreen", "0"];
  const serverArgs = [
    "-stdout", "-iwad", profileData.iwad, "-file", ...(profileData.files || []),
    "-host", "8", "-port", String(options.gamePort), "-lastmanstanding",
    "+set", "sv_updatemaster", "0",
    "+set", "sv_noplayertimeout", "1",
    // The scenario injects many bridge commands; disable the client command
    // flood ban so the disconnect/reconnect probe is not kicked mid-run.
    "+set", "sv_limitcommands", "0",
    "+set", "sv_cheats", "1",
    "+set", "uh_sv_loglevel", "4",
    // A round timer would force an ending mid-scenario; the watchers own the
    // round end in this test.
    "+set", "uh_sv_gametimer", "0",
    "+set", "uh_sv_resumeonrevive", "1",
    "+set", "uh_sv_multiboss", String(FORCED_BOSSES.length),
    ...FORCED_BOSSES.flatMap((entry, index) => [
      "+set", "uh_sv_forcedboss" + (index + 1), String(entry.boss),
      "+set", "uh_sv_forcebossplayer" + (index + 1), String(entry.player),
    ]),
    "+map", map,
    ...common,
  ];
  dedicated = spawn(join(serverDir, "zandronum"), serverArgs, {
    cwd: serverDir,
    env: { ...process.env, SDL_VIDEODRIVER: "offscreen", ZANDRONUM_BRIDGE_PORT: String(SERVER_BRIDGE_PORT) },
    stdio: ["pipe", "pipe", "pipe"],
  });
  for (const stream of [dedicated.stdout, dedicated.stderr]) {
    stream.on("data", (chunk) => {
      dedicatedLog = (dedicatedLog + chunk).slice(-400000);
      appendFileSync(serverLogPath, chunk);
    });
  }

  await client.connect(transport);

  // The map must be loaded before any map variable can be read.
  await waitFor("server map load", async () => {
    const over = await trySrvMapVar("gameover");
    return over === null ? null : { gameover: over };
  }, 180_000, 1_000);
  launched.push(CLIENT_INSTANCE);
  await tool("launch_instance", launchInstanceArgs(CLIENT_INSTANCE, profileData, [
    ...common, "+set", "uh_cl_LogLevel", "4", "-port", String(options.gamePort + 1), "+name", "LMSClient",
  ]), 150_000);
  await waitFor("client engine live", async () => tryActorState(CLIENT_INSTANCE), 90_000, 500);
  // A launched single-player engine pauses when its window is not focused, and
  // a headless (offscreen) window is never focused. Unpause it before the
  // connect: a paused client accepts the console command but runs no tics, so
  // the level authentication below would never complete.
  await clientTool("set_pause", { paused: false }, 10_000).catch(() => null);

  await joinOngoingRound();
  const clientActor = await waitFor("client spawn", async () => {
    const state = await tryActorState(CLIENT_INSTANCE);
    return state && Number(state.health) > 0 ? state : null;
  }, 90_000, 500);
  const clientTid = Number(clientActor.tid);
  const clientSlot = clientTid - 1000;
  if (!(clientSlot >= 0 && clientSlot < MAX_PLAYERS)) throw new Error("unexpected client TID " + clientTid);
  check("client owns a player slot before bots join", clientSlot === 0, { clientTid, clientSlot });

  for (let bot = 0; bot < TOTAL_BOTS; bot += 1) await serverCommand("addbot", 1200);

  const roundCounters = await waitFor("round start", async () => {
    const survivor = await trySrvMapArray("totalplayersarr", PLS_SURVIVOR);
    const boss = await trySrvMapArray("totalplayersarr", PLS_BOSS);
    if (survivor === null || boss === null) return null;
    return survivor >= SURVIVOR_BOTS + 1 && boss === FORCED_BOSSES.length ? { survivor, boss } : null;
  }, 240_000, 1_000);

  const clientRole = await srvMapArray("playerlifestatusarr", clientSlot);
  const gameover = await srvMapVar("gameover");
  const settlementPending = await srvMapArray("uh_settlementstate", SETTLE_PENDING);
  const liveState = await actorState(CLIENT_INSTANCE);
  const serverSideState = await trySrvActorState(clientTid);
  const startHud = hudMessages(await clientTool("read_hud", {}, 20_000).catch(() => null));

  check("round is in progress", gameover === 0 && settlementPending === 0,
    { gameover, settlementPending, counters: roundCounters });
  check("client pawn is alive", Number(liveState.health) > 0,
    { class: liveState.class, health: liveState.health });
  check("server agrees on the client class", !!serverSideState && serverSideState.class === liveState.class,
    { client: liveState.class, server: serverSideState && serverSideState.class });
  check("client holds the Survivor role", clientRole === PLS_SURVIVOR, { clientSlot, clientRole });
  check("boss slots hold the forced boss count", roundCounters.boss === FORCED_BOSSES.length, roundCounters);
  check("survivor side holds the client and the survivor bots",
    roundCounters.survivor >= SURVIVOR_BOTS + 1, roundCounters);

  const clientRoleCache = await waitFor("client role cache", async () => {
    const roles = [];
    for (let slot = 0; slot < 5; slot += 1) roles.push(await tryClientMapArray("uhtirole", slot));
    return roles.includes(PLS_BOSS) && roles.includes(PLS_SURVIVOR) ? roles : null;
  }, 90_000, 1_000);
  check("client receives both roles over the network",
    clientRoleCache.includes(PLS_BOSS) && clientRoleCache.includes(PLS_SURVIVOR), { roles: clientRoleCache });

  // --- phase 2: boss morph --------------------------------------------------
  const bossStates = [];
  for (let index = 0; index < FORCED_BOSSES.length; index += 1) {
    const forced = FORCED_BOSSES[index];
    const tid = 1000 + forced.player;
    const bossState = await waitFor("boss " + (index + 1) + " morph", async () => {
      const state = await trySrvActorState(tid);
      return state && state.class === forced.actor ? state : null;
    }, 90_000, 500);
    // The ready weapon is equipped a tick or more after the class changes; give
    // it a short bounded window instead of sampling the exact morph frame.
    const armedState = await waitFor("boss " + (index + 1) + " ready weapon", async () => {
      const state = await trySrvActorState(tid);
      return state && state.weapon ? state : null;
    }, 15_000, 500).catch(() => null);
    const remote = await tryActorState(CLIENT_INSTANCE, tid);
    bossStates.push({
      tid,
      expected: forced.actor,
      serverClass: bossState.class,
      serverHealth: bossState.health,
      clientClass: remote ? remote.class : null,
      morphedFlag: hasInventory(bossState, "MorphedFlag"),
      bossWeapon: (armedState && armedState.weapon) || bossState.weapon || null,
    });
  }
  check("forced bosses morphed into their actor class",
    bossStates.every((entry) => entry.serverClass === entry.expected), bossStates);
  check("boss morph is visible on the remote client",
    bossStates.every((entry) => entry.clientClass === entry.expected),
    bossStates.map((entry) => ({ tid: entry.tid, expected: entry.expected, client: entry.clientClass })));
  // BasicBossItem is a CustomInventory: it runs its Use state and is consumed,
  // so it is never observable afterwards.  MorphedFlag is the persistent morph
  // marker, and a real boss carries its own weapon instead of the survivor one.
  check("bosses carry the boss morph state",
    bossStates.every((entry) => entry.morphedFlag && entry.bossWeapon),
    bossStates.map((entry) => ({ tid: entry.tid, MorphedFlag: entry.morphedFlag, weapon: entry.bossWeapon })));

  // rz_debug_MorphMe runs on the server (a client puke is forwarded with this
  // client's pawn as activator), so this is a real server-side morph of a
  // live player, and the class change must reach the remote client.
  const beforeMorphClass = liveState.class;
  await clientTool("run_script", { script: "rz_debug_MorphMe", args: [0, 51], always: true }, 30_000);
  const debugMorph = await waitFor("debug morph", async () => {
    const live = await tryActorState(CLIENT_INSTANCE);
    const serverSide = await trySrvActorState(clientTid);
    return live && serverSide && live.class !== beforeMorphClass && serverSide.class === live.class
      ? { live, serverSide } : null;
  }, 60_000, 500);
  check("rz_debug_MorphMe changes a live player class on both sides",
    debugMorph.live.class !== beforeMorphClass && debugMorph.serverSide.class === debugMorph.live.class,
    { before: beforeMorphClass, client: debugMorph.live.class, server: debugMorph.serverSide.class });
  const debugArmed = await waitFor("debug morph ready weapon", async () => {
    const state = await trySrvActorState(clientTid);
    return state && state.weapon ? state : null;
  }, 15_000, 500).catch(() => null);
  check("debug morph sets the boss morph state",
    hasInventory(debugMorph.serverSide, "MorphedFlag")
      && !!((debugArmed && debugArmed.weapon) || debugMorph.serverSide.weapon),
    { class: debugMorph.serverSide.class, weapon: (debugArmed && debugArmed.weapon) || debugMorph.serverSide.weapon });
  // An unmatched boss id keeps the unmorph but skips the morph, so the player
  // returns to the survivor class instead of staying in a test body.
  await clientTool("run_script", { script: "rz_debug_MorphMe", args: [0, 30000], always: true }, 30_000);
  const restoredState = await waitFor("debug unmorph", async () => {
    const live = await tryActorState(CLIENT_INSTANCE);
    return live && live.class === beforeMorphClass ? live : null;
  }, 60_000, 500);
  check("an unmatched boss id restores the survivor class",
    restoredState.class === beforeMorphClass, { class: restoredState.class, health: restoredState.health });

  // --- phase 4: mid-round disconnect and reconnect -------------------------
  const roundMarkers = async () => ({
    winstreak: await trySrvMapVar("winstreak"),
    bossTid: await trySrvMapArray("bossdataarr", 0),
    bossCount: await trySrvMapArray("totalplayersarr", PLS_BOSS),
    gameover: await trySrvMapVar("gameover"),
    generation: await trySrvMapArray("uh_settlementstate", SETTLE_GENERATION),
  });
  const markersBefore = await roundMarkers();
  const bossTidBefore = markersBefore.bossTid;
  const disconnectLogStart = readServerLog().length;
  await clientTool("run_command", { text: "disconnect" }, 20_000);
  const disconnectEvidence = await waitFor("client disconnect seen by server", async () => {
    const log = readServerLog().slice(disconnectLogStart);
    const left = /LMSClient[^\n]*(left the game|disconnected|has left)/i.test(log);
    const role = await trySrvMapArray("playerlifestatusarr", clientSlot);
    const cleared = role === PLS_DEAD || role === PLS_NULL;
    return left || cleared ? { left, role, cleared } : null;
  }, 60_000, 500);
  check("server clears the client role on disconnect", disconnectEvidence.cleared,
    disconnectEvidence);
  const markersDuring = await waitFor("round survives the disconnect", async () => {
    const markers = await roundMarkers();
    return markers.gameover === 0 && markers.bossCount === FORCED_BOSSES.length ? markers : null;
  }, 60_000, 500);
  check("disconnect does not end the round",
    markersDuring.gameover === 0 && markersDuring.bossCount === FORCED_BOSSES.length,
    { markersBefore, markersDuring, disconnectEvidence });

  await joinOngoingRound();
  const rejoined = await waitFor("rejoin", async () => {
    const role = await trySrvMapArray("playerlifestatusarr", clientSlot);
    const state = await tryActorState(CLIENT_INSTANCE);
    return role === PLS_SURVIVOR && state && Number(state.health) > 0 ? { role, state } : null;
  }, 120_000, 500);
  const markersAfter = await roundMarkers();
  check("client rejoins as a living survivor",
    rejoined.role === PLS_SURVIVOR && Number(rejoined.state.health) > 0,
    { role: rejoined.role, class: rejoined.state.class, health: rejoined.state.health });
  check("round state survived the reconnect",
    markersAfter.gameover === 0 &&
      markersAfter.bossCount === markersBefore.bossCount &&
      markersAfter.bossTid === bossTidBefore &&
      markersAfter.winstreak === markersBefore.winstreak &&
      markersAfter.generation === markersBefore.generation,
    { before: markersBefore, after: markersAfter });

  // --- phase 3: settlement window and revival cancellation -----------------
  const survivorSlots = [];
  for (let slot = 0; slot < MAX_PLAYERS; slot += 1) {
    if (await trySrvMapArray("playerlifestatusarr", slot) === PLS_SURVIVOR) survivorSlots.push(slot);
  }
  check("survivor slots discovered", survivorSlots.length === SURVIVOR_BOTS + 1, { survivorSlots });
  for (const slot of survivorSlots) await serverCommand("pukename rz_debug_KillPlayerSlot " + slot, 600);

  const settled = await waitFor("settlement window", async () => {
    const pending = await trySrvMapArray("uh_settlementstate", SETTLE_PENDING);
    const survivors = await trySrvMapArray("totalplayersarr", PLS_SURVIVOR);
    return pending === 1 && survivors === 0 ? { pending, survivors } : null;
  }, 60_000, 250);
  const settlementStarted = await srvMapArray("uh_settlementstate", SETTLE_STARTED);
  const settlementDeadline = await srvMapArray("uh_settlementstate", SETTLE_DEADLINE);
  const gameoverPending = await srvMapVar("gameover");
  const pendingHud = hudMessages(await clientTool("read_hud", {}, 20_000).catch(() => null));
  check("settlement window entered after the survivor side empties",
    settled.pending === 1 && settled.survivors === 0,
    { pending: settled.pending, survivors: settled.survivors, started: settlementStarted, deadline: settlementDeadline });
  check("round is not final while the window is open", gameoverPending === 0, { gameover: gameoverPending });
  check("the client HUD shows the pending result",
    pendingHud.some((message) => /have been defeated|victorious/i.test(message.text)),
    { messages: pendingHud.map((message) => message.text) });

  // A real Dickhead revival (the production rescue path, not a state write)
  // puts one survivor back inside the window.
  const revivalVictim = survivorSlots[survivorSlots.length - 1];
  const revivalSourceTid = Number(bossStates[0].tid);
  await serverCommand("pukename rz_DickheadRevivalDelayed always " + revivalVictim + " " + revivalSourceTid, 500);
  const cancelled = await waitFor("settlement cancellation", async () => {
    const pending = await trySrvMapArray("uh_settlementstate", SETTLE_PENDING);
    const survivors = await trySrvMapArray("totalplayersarr", PLS_SURVIVOR);
    const over = await trySrvMapVar("gameover");
    return pending === 0 && survivors >= 1 && over === 0 ? { pending, survivors, over } : null;
  }, 60_000, 250);
  check("a revival inside the window cancels the settlement",
    cancelled.pending === 0 && cancelled.survivors >= 1 && cancelled.over === 0, cancelled);
  const cancelledLog = readServerLog();
  check("the round core logs the cancellation",
    /Opposing sides returned; round settlement cancelled/.test(cancelledLog),
    cancelledLog.split(/\r?\n/).filter((line) => /opposing sides|settlement|revived/i.test(line)).slice(-6));
  const clearedHud = hudMessages(await clientTool("read_hud", {}, 20_000).catch(() => null));
  check("the pending result HUD is cleared after the cancellation",
    !clearedHud.some((message) => /have been defeated/i.test(message.text)),
    { messages: clearedHud.map((message) => message.text) });

  // --- phase 5: teardown ----------------------------------------------------
  await teardownEngines();
  check("client instance quit cleanly", /quit cleanly/.test(String(cleanup.client || "")),
    { client: cleanup.client });
  check("dedicated server process exited", cleanup.serverExited === true, { server: cleanup.server });
  const openPorts = [];
  for (const port of [SERVER_BRIDGE_PORT, CLIENT_BRIDGE_PORT]) {
    if (!(await portIsFree(port))) openPorts.push(port);
  }
  check("no engine bridge port is left listening", openPorts.length === 0, { openPorts });

  result = result || {};
  result.debug = { startHud, clientActor, liveState, bossStates, pendingHud, cancelled };
} catch (error) {
  result = {
    status: "error",
    ok: false,
    error: error instanceof Error ? error.message : String(error),
    assertions,
    serverStderr,
    serverLogTail: dedicatedLog.split(/\r?\n/).slice(-40),
    failedAssertions: assertions.filter((a) => !a.pass).map((a) => a.name),
  };
} finally {
  // Safety net: phase 5 normally already tore everything down, and the helper
  // is idempotent, so a thrown assertion still cannot leave an engine running.
  try { await teardownEngines(); } catch { /* best effort */ }
  if (!options.keepLogs && isolatedRoot) rmSync(isolatedRoot, { recursive: true, force: true });
  else if (isolatedRoot) console.error("kept isolated folder: " + isolatedRoot);
}

const passed = assertions.filter((a) => a.pass).length;
const failed = assertions.length - passed;
if (result && result.status !== "error") {
  result = {
    status: failed === 0 ? "pass" : "fail",
    ok: failed === 0,
    profile: options.profile,
    gamePort: options.gamePort,
    engine: ENGINE,
    duration_s: Math.round(((Date.now() - startedAt) / 1000) * 100) / 100,
    passed,
    failed,
    assertions,
    failedAssertions: assertions.filter((a) => !a.pass).map((a) => a.name),
    cleanup,
    serverLogTail: readServerLog().split(/\r?\n/).slice(-25),
    serverLogPath: options.keepLogs ? serverLogPath : null,
    debug: result.debug,
  };
} else if (result) {
  result.duration_s = Math.round(((Date.now() - startedAt) / 1000) * 100) / 100;
  result.cleanup = cleanup;
  result.passed = passed;
  result.failed = failed;
}
console.log(options.json ? JSON.stringify(result) : JSON.stringify(result, null, 2));
process.exitCode = result && result.ok ? 0 : 1;