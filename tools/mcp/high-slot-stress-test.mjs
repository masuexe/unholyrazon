#!/usr/bin/env node
//
// high-slot-stress-test.mjs - high-slot player load and map reload on v6c.
//
// Starts one dedicated LMS server with sv_maxclients/sv_maxplayers 64 and one
// real connected client, adds 63 bots, then reloads the map. It asserts that:
//   - the server accepts a full 64-player roster without an ACS VM fault;
//   - UH role bookkeeping covers the high slots (playerlifestatusarr max id);
//   - a console map reload rebuilds the round state and keeps the server alive.
// It does not run a full round; combat scheduling is not asserted.
//
// STATUS: NOT A GATE CHECK. v6c runs accepted 63 addbot commands and the server
// stayed alive through the roster and the map reload, with no ACS VM fault. The
// role snapshot did not reach 64 players because playerlifestatusarr rebuilds
// only at a round setup: paced bots produced max slot 35 with 27 assigned sides,
// and a burst produced no round snapshot inside the window. Add the bots before
// the first round setup (or force a fresh round) before registering this script
// in tools/gate.py.
//
// Usage:
//   node tools/mcp/high-slot-stress-test.mjs [--json] [--map NAME] [--port N]
//
// Env: ZANDRONUM_EXE, ZANDRONUM_LAUNCH_PROFILES (default v6c smoke profile).
import { spawn } from "node:child_process";
import { appendFileSync, cpSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadResolvedProfile } from "../resolve-launch-profile.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const PROFILES = resolve(ROOT, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const ENGINE = process.env.ZANDRONUM_EXE;
if (!ENGINE) throw new Error("set ZANDRONUM_EXE to the bridge-patched Zandronum binary");

const options = { json: false, map: "MMCTF26", port: 10990, bots: 63 };
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === "--json") { options.json = true; continue; }
  if (arg === "--map") { options.map = process.argv[++i] || ""; continue; }
  if (arg === "--port") { options.port = Number.parseInt(process.argv[++i], 10); continue; }
  if (arg === "--bots") { options.bots = Number.parseInt(process.argv[++i], 10); continue; }
  if (arg === "--help" || arg === "-h") {
    console.log("Usage: high-slot-stress-test.mjs [--json] [--map NAME] [--port N] [--bots N]");
    process.exit(0);
  }
  throw new Error("unknown option " + arg);
}
if (!options.map || !Number.isInteger(options.port) || !Number.isInteger(options.bots)) throw new Error("invalid options");

const { profile } = loadResolvedProfile(ROOT, PROFILES, "mm8bdm-v6c-smoke");
const common = ["-nosound", "+set", "vid_renderer", "0", "+set", "fullscreen", "0"];
const isolatedRoot = mkdtempSync(join(tmpdir(), "uh-highslot-"));
const serverDir = join(isolatedRoot, "server");
const clientDir = join(isolatedRoot, "client");
const serverLogPath = join(isolatedRoot, "server.log");
cpSync(dirname(ENGINE), serverDir, { recursive: true });
cpSync(dirname(ENGINE), clientDir, { recursive: true });
appendFileSync(serverLogPath, "");

const assertions = [];
function check(name, pass, detail) {
  assertions.push({ name, pass: !!pass, detail });
  if (!options.json) console.error("[" + (pass ? "PASS" : "FAIL") + "] " + name + (detail === undefined ? "" : " :: " + JSON.stringify(detail)));
}
const delay = (ms) => new Promise((resolveDelay) => setTimeout(resolveDelay, ms));
const readServerLog = () => { try { return readFileSync(serverLogPath, "utf8"); } catch { return ""; } };

let dedicated = null;
let client = null;
let clientLog = "";
const cleanup = { client: null, serverExited: false };
const SENTINEL = "__HS_BLOCK_DONE__";

function sendServer(line) {
  if (!dedicated || !dedicated.stdin || !dedicated.stdin.writable) throw new Error("server stdin not writable");
  dedicated.stdin.write(line + "\n");
}
async function serverOutput(command, timeoutMs = 20_000) {
  const start = readServerLog().length;
  sendServer(command + "; echo " + SENTINEL);
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    await delay(100);
    if (dedicated.exitCode !== null) throw new Error("server exited while running: " + command);
    const out = readServerLog().slice(start);
    const end = out.indexOf(SENTINEL);
    if (end >= 0) return out.slice(0, end);
  }
  throw new Error("server console timed out: " + command);
}
async function srvMapVar(name) {
  const out = await serverOutput("getmapvar " + name);
  const match = out.match(new RegExp("mapvar " + name + " = (-?\\d+)"));
  if (!match) throw new Error("getmapvar " + name + " gave no value");
  return Number(match[1]);
}
async function trySrvMapVar(name) { try { return await srvMapVar(name); } catch { return null; } }
async function srvMapArray(name, index) {
  const out = await serverOutput("getmaparray " + name + " " + index);
  const match = out.match(new RegExp("maparray " + name + "\\[" + index + "\\] = (-?\\d+)"));
  if (!match) throw new Error("getmaparray " + name + "[" + index + "] gave no value");
  return Number(match[1]);
}
async function trySrvMapArray(name, index) { try { return await srvMapArray(name, index); } catch { return null; } }
async function waitForLog(pattern, timeoutMs, label) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (pattern.test(readServerLog())) return true;
    await delay(200);
  }
  throw new Error(label + " timed out after " + timeoutMs + "ms");
}
const VM_ERROR = /out of bounds access|ACS VM|script error|invalid array|array index|Execution could not continue/i;

let result;
let finalServerLog = "";
let finalClientLog = "";
try {
  const serverArgs = ["-stdout", "-iwad", profile.iwad, "-file", ...(profile.files || []),
    "-host", "-port", String(options.port), "-lastmanstanding",
    "+set", "sv_updatemaster", "0", "+set", "sv_noplayertimeout", "1",
    "+set", "sv_cheats", "1", "+set", "sv_limitcommands", "0",
    "+set", "sv_maxclients", "64", "+set", "sv_maxplayers", "64",
    "+set", "uh_sv_gametimer", "0",
    "+map", options.map, ...common];
  dedicated = spawn(join(serverDir, "zandronum"), serverArgs, {
    cwd: serverDir,
    env: { ...process.env, SDL_VIDEODRIVER: "offscreen" },
    stdio: ["pipe", "pipe", "pipe"],
  });
  for (const stream of [dedicated.stdout, dedicated.stderr]) stream.on("data", (chunk) => appendFileSync(serverLogPath, chunk));
  await waitForLog(new RegExp("\\*\\*\\* " + options.map), 120_000, "server map load");

  client = spawn(join(clientDir, "zandronum"), ["-stdout", "-iwad", profile.iwad, "-file", ...(profile.files || []),
    ...common, "-port", String(options.port + 1), "+name", "StressClient", "+connect", "127.0.0.1:" + options.port], {
    cwd: clientDir,
    env: { ...process.env, SDL_VIDEODRIVER: "offscreen" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  for (const stream of [client.stdout, client.stderr]) stream.on("data", (chunk) => { clientLog = (clientLog + chunk).slice(-200000); });
  const clientDeadline = Date.now() + 120_000;
  while (Date.now() < clientDeadline && !/Snapshot received\./.test(clientLog)) {
    if (client.exitCode !== null) throw new Error("client exited during connect: " + clientLog.slice(-2000));
    await delay(250);
  }
  if (!/Snapshot received\./.test(clientLog)) throw new Error("client did not receive a snapshot");
  check("a real client connects to the server", true);

  // Burst the addbot lines so the server console drains them during the
  // pre-round window instead of after the round has already frozen its roster.
  dedicated.stdin.write(Array.from({ length: options.bots }, () => "addbot").join("\n") + "\n");
  await delay(12_000);
  // Late bots may join as spectators until the next round setup assigns sides.
  const slotsDeadline = Date.now() + 30_000;
  let maxSlot = await trySrvMapArray("playerlifestatusarr", 64);
  while (Date.now() < slotsDeadline && !(Number.isInteger(maxSlot) && maxSlot >= 55)) {
    await delay(500);
    maxSlot = await trySrvMapArray("playerlifestatusarr", 64);
  }
  const survivors = await trySrvMapArray("totalplayersarr", 1);
  const bosses = await trySrvMapArray("totalplayersarr", 2);
  const gameover = await trySrvMapVar("gameover");
  const logAfterBots = readServerLog();
  check("the server survives the 64-player roster",
    dedicated.exitCode === null && !VM_ERROR.test(logAfterBots.slice(logAfterBots.length - 120000)),
    { exitCode: dedicated.exitCode, bots: options.bots });
  check("UH role bookkeeping reaches the high player slots",
    Number.isInteger(maxSlot) && maxSlot >= 55,
    { maxSlot, survivors, bosses, gameover });
  check("the roster is assigned to round sides",
    (survivors || 0) + (bosses || 0) >= 55,
    { survivors, bosses, gameover });

  const reloadStart = readServerLog().length;
  sendServer("map MMDOM01");
  await waitForLog(new RegExp("\\*\\*\\* MMDOM01"), 120_000, "map reload");
  const reloadDeadline = Date.now() + 60_000;
  let reloadMaxSlot = await trySrvMapArray("playerlifestatusarr", 64);
  while (Date.now() < reloadDeadline && !(Number.isInteger(reloadMaxSlot) && reloadMaxSlot >= 55)) {
    await delay(500);
    reloadMaxSlot = await trySrvMapArray("playerlifestatusarr", 64);
  }
  const reloadLog = readServerLog().slice(reloadStart);
  const reloadGameover = await trySrvMapVar("gameover");
  check("a console map reload keeps the server alive",
    dedicated.exitCode === null && !VM_ERROR.test(reloadLog),
    { exitCode: dedicated.exitCode });
  check("the reloaded map starts a fresh, high-slot round",
    reloadGameover === 0 && Number.isInteger(reloadMaxSlot) && reloadMaxSlot >= 55,
    { gameover: reloadGameover, maxSlot: reloadMaxSlot });
} catch (error) {
  result = { status: "error", ok: false, error: error instanceof Error ? error.message : String(error), assertions, serverLogTail: finalServerLog.split(/\r?\n/).slice(-40), clientLogTail: finalClientLog.split(/\r?\n/).slice(-30) };
} finally {
  try {
    if (client && client.exitCode === null) {
      client.kill("SIGTERM");
      await Promise.race([new Promise((r) => client.once("exit", r)), delay(3000)]);
      if (client.exitCode === null) client.kill("SIGKILL");
    }
    cleanup.client = "client process exited";
  } catch { /* best effort */ }
  try {
    if (dedicated && dedicated.exitCode === null) {
      sendServer("quit");
      await Promise.race([new Promise((r) => dedicated.once("exit", r)), delay(5000)]);
      if (dedicated.exitCode === null) dedicated.kill("SIGKILL");
    }
    cleanup.serverExited = true;
  } catch { /* best effort */ }
  finalServerLog = readServerLog();
  finalClientLog = clientLog;
  try { rmSync(isolatedRoot, { recursive: true, force: true }); } catch { /* best effort */ }
}

const passed = assertions.filter((a) => a.pass).length;
const failed = assertions.length - passed;
if (!result) {
  result = { status: failed === 0 ? "pass" : "fail", profile: "mm8bdm-v6c-smoke", map: options.map, bots: options.bots, passed, failed, assertions, serverLogTail: finalServerLog.split(/\r?\n/).slice(-40), clientLogTail: finalClientLog.split(/\r?\n/).slice(-30) };
} else {
  result.passed = passed;
  result.failed = failed;
}
console.log(options.json ? JSON.stringify(result) : JSON.stringify(result, null, 2));
process.exitCode = result.ok === false || failed ? 1 : 0;
