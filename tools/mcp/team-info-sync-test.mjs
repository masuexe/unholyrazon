#!/usr/bin/env node
//
// team-info-sync-test.mjs - runtime regression gate for the Unholy team-info
// CLIENTSIDE sync delivery ("P1 fix - per-client delivery for CLIENTSIDE
// receivers").
//
// Why this exists: the team-info receivers (uh_ti_sync_status, uh_ti_sync_ova,
// uh_ti_sync_policy, uh_ti_stat, uh_ti_stat_clear) are CLIENTSIDE scripts.  A
// plain ACS_NamedExecuteAlways call to a CLIENTSIDE script does not reach a
// remote client on a dedicated/listen server, so the client cache stayed at
// PLS_NULL / INVALID.  This test drives a real remote client and asserts every
// receiver's observable effect.  It cannot be proven by static compilation.
//
// Coverage:
//   1. spectator hello  - a client that connects but never spawns still gets a
//      full snapshot (uhtiova/uhtiovatarget), proving the server watch path.
//   2. spectator stats  - a true spectator receives uh_ti_stat for in-game
//      subjects; removing a bot then produces uh_ti_stat_clear.
//   3. local receiver   - uh_ti_stat / uh_ti_stat_clear round-trip directly on
//      the client VM (deterministic receiver coverage).
//   4. join snapshot    - after the console 'join' the client spawns and the
//      role/policy/life snapshot is populated.
//
// Usage:
//   node tools/mcp/team-info-sync-test.mjs [--profile NAME] [--game-port N]
//        [--bridge-port N] [--stress] [--json] [--dry-run]
//
// Env overrides (same family as the other tools/mcp scripts):
//   ZANDRONUM_MCP_DIR, ZANDRONUM_MCP_SERVER, ZANDRONUM_EXE,
//   ZANDRONUM_LAUNCH_PROFILES, ZANDRONUM_BRIDGE_PORT.

import { spawn } from "node:child_process";
import { appendFileSync, cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { launchInstanceArgs, loadResolvedProfile } from "../resolve-launch-profile.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const PROFILES = resolve(ROOT, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const RUNNER = join(ROOT, "tools/mcp/server-runner.mjs");
const SERVER_LOG = "/tmp/team-info-sync-server.log";
const STAT_SLOTS = 8;

function usage() {
  return "Usage: team-info-sync-test.mjs [--profile NAME] [--game-port N] [--bridge-port N] [--stress] [--json] [--dry-run]\n" +
    "\n" +
    "Launch one local Zandronum listen server plus one MCP-controlled remote client,\n" +
    "then verify every team-info CLIENTSIDE receiver over the network: the spectator\n" +
    "hello, uh_ti_sync_status / uh_ti_sync_ova / uh_ti_sync_policy after join, and\n" +
    "uh_ti_stat / uh_ti_stat_clear via a spectator observing a bot that is removed.\n" +
    "--stress also fills 33/64 slots with bots, checks server execution budgets,\n" +
    "then verifies a full-server map reload and spectator reconnect.\n" +
    "Requires local TCP/UDP ports and the bridge-patched engine.\n";
}

const options = { profile: "mm8bdm-v6c-smoke", gamePort: 10767, bridgePort: 7777, stress: false, json: false, dryRun: false };
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === "--help" || arg === "-h") { console.log(usage()); process.exit(0); }
  if (arg === "--json") { options.json = true; continue; }
  if (arg === "--dry-run") { options.dryRun = true; continue; }
  if (arg === "--stress") { options.stress = true; continue; }
  if (arg === "--profile") { options.profile = process.argv[++i] || ""; continue; }
  if (arg === "--game-port") { options.gamePort = Number.parseInt(process.argv[++i], 10); continue; }
  if (arg === "--bridge-port") { options.bridgePort = Number.parseInt(process.argv[++i], 10); continue; }
  throw new Error("unknown option " + arg);
}
if (!options.profile) throw new Error("invalid --profile");
for (const pair of [["--game-port", options.gamePort], ["--bridge-port", options.bridgePort]]) {
  if (!Number.isInteger(pair[1]) || pair[1] < 1024 || pair[1] > 65535) throw new Error("invalid " + pair[0]);
}
const MCP_DIR = process.env.ZANDRONUM_MCP_DIR;
if (!MCP_DIR) throw new Error("set ZANDRONUM_MCP_DIR to your ZandronumMCP checkout");
const SERVER = process.env.ZANDRONUM_MCP_SERVER || join(MCP_DIR, "dist/server.js");
const ENGINE = process.env.ZANDRONUM_EXE;
if (!ENGINE) throw new Error("set ZANDRONUM_EXE to the bridge-patched Zandronum binary");
const SDK = join(MCP_DIR, "node_modules/@modelcontextprotocol/sdk/dist/esm");
for (const path of [SERVER, ENGINE, PROFILES, RUNNER]) if (!existsSync(path)) throw new Error("missing path: " + path);
if (options.dryRun) {
  console.log(JSON.stringify({ status: "dry-run", profile: options.profile, gamePort: options.gamePort, bridgePort: options.bridgePort, server: SERVER, engine: ENGINE }));
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
  env: { ...process.env, ZANDRONUM_EXE: ENGINE, ZANDRONUM_LAUNCH_PROFILES: PROFILES, ZANDRONUM_BRIDGE_PORT: String(options.bridgePort) },
  stderr: "pipe",
});
let stderr = "";
transport.stderr?.on("data", chunk => { stderr = (stderr + chunk).slice(-12000); });

const client = new Client({ name: "unholy-team-info-sync", version: "1.0.0" });
const delay = ms => new Promise(r => setTimeout(r, ms));
const launched = [];
let dedicated;
let isolatedRoot;
let dedicatedLog = "";
const text = result => (result.content || []).filter(x => x.type === "text").map(x => x.text).join("\n");

async function tool(name, args, timeout) {
  const result = await client.callTool({ name, arguments: args }, undefined, { timeout: timeout || 90_000 });
  if (result.isError) throw new Error(name + ": " + text(result));
  return result;
}
async function mapVar(name) {
  try { const r = await tool("get_map_var", { instance: 1, name }, 8_000); return r.structuredContent?.value ?? Number(text(r)); }
  catch { return null; }
}
async function mapArray(name, index) {
  try { const r = await tool("get_map_array", { instance: 1, name, index }, 8_000); return r.structuredContent?.value ?? Number(text(r)); }
  catch { return null; }
}
async function statValids() {
  const out = [];
  for (let k = 0; k < STAT_SLOTS; k += 1) out.push(await mapArray("uhtistatvalid", k));
  return out;
}
async function roleSnapshot() {
  const out = { policy: await mapVar("uhtiscorepolicy"), ova: await mapVar("uhtiova"), target: await mapVar("uhtiovatarget"), role: [], life: [] };
  for (let k = 0; k < STAT_SLOTS; k += 1) { out.role.push(await mapArray("uhtirole", k)); out.life.push(await mapArray("uhtilife", k)); }
  return out;
}

const common = ["-nosound", "+set", "vid_renderer", "0", "+set", "fullscreen", "0"];
let result;
try {
  await client.connect(transport);
  const { profile: profileData } = loadResolvedProfile(ROOT, PROFILES, options.profile);

  // Bridge-controlled remote client first (matches the other tools/mcp tests).
  launched.push(1);
  await tool("launch_instance", launchInstanceArgs(1, profileData, [
    ...common, "+set", "uh_cl_teaminfo", "1", "-port", String(options.gamePort + 1), "+name", "TeamInfoClient",
  ]), 120_000);
  await delay(8_000);

  isolatedRoot = mkdtempSync(join(tmpdir(), "unholy-teaminfo-"));
  const serverDir = join(isolatedRoot, "server");
  cpSync(dirname(ENGINE), serverDir, { recursive: true });
  writeFileSync(SERVER_LOG, "");
  const serverArgs = [
    "-stdout", "-iwad", profileData.iwad, "-file", ...(profileData.files || []),
    "-host", options.stress ? "64" : "8", "-port", String(options.gamePort), "-lastmanstanding",
    ...(options.stress ? ["+set", "sv_maxplayers", "64", "+set", "bot_allowchat", "0"] : []),
    "+set", "sv_minplayers", "1", "+set", "sv_updatemaster", "0", "+set", "sv_noplayertimeout", "1",
    "+set", "sv_cheats", "1", "+map", profileData.map || "MM2DW1", ...common,
  ];
  dedicated = spawn(join(serverDir, "zandronum"), serverArgs, {
    cwd: serverDir,
    env: { ...process.env, SDL_VIDEODRIVER: "offscreen", ZANDRONUM_BRIDGE_PORT: String(options.gamePort + 100) },
    stdio: ["pipe", "pipe", "pipe"],
  });
  for (const stream of [dedicated.stdout, dedicated.stderr]) {
    stream.on("data", chunk => { dedicatedLog = (dedicatedLog + chunk).slice(-400000); appendFileSync(SERVER_LOG, chunk); });
  }
  const sendServer = line => { if (dedicated.stdin.writable) dedicated.stdin.write(line + "\n"); };
  await delay(25_000);
  if (dedicated.exitCode !== null) throw new Error("listen server exited early with code " + dedicated.exitCode);

  const connectOut = await tool("run_command", { instance: 1, text: "connect 127.0.0.1:" + options.gamePort }, 25_000).then(text);
  await delay(12_000);

  // --- Phase 1: spectator hello (client connected, has NOT joined) ----------
  let spectator = { policy: null, ova: null, target: null };
  for (let i = 0; i < 20; i += 1) {
    spectator = { policy: await mapVar("uhtiscorepolicy"), ova: await mapVar("uhtiova"), target: await mapVar("uhtiovatarget") };
    if (spectator.policy !== null && spectator.policy !== -1) break;
    await delay(3_000);
  }
  const spectatorHello = spectator.policy !== null && spectator.policy !== -1
    && spectator.ova !== null && spectator.target !== null;

  // --- Phase 2: spectator receives roles + uh_ti_stat; a removal clears it ----
  sendServer("addbot");
  await delay(2_000);
  sendServer("addbot");
  await delay(6_000);
  // A bot that joins mid-round does not get playerlifestatusarr assigned (the
  // rebuild path early-returns outside a bonus event), so force the round's
  // role gather + FullSnapshot, as the directed versus test does, to prove
  // uh_ti_sync_status reaches a true spectator.
  sendServer("pukename ub_StartUpSettings");

  let statSlots = [];
  let spectatorRoles = [];
  for (let i = 0; i < 15; i += 1) {
    await delay(3_000);
    statSlots = await statValids();
    spectatorRoles = [];
    for (let k = 0; k < STAT_SLOTS; k += 1) spectatorRoles.push(await mapArray("uhtirole", k));
    const statsSeeded = statSlots.filter(v => v === true || v === 1).length >= 2;
    const rolesSeen = spectatorRoles.some(v => v !== null && v !== -1);
    if (statsSeeded && rolesSeen) break;
  }
  const seededSlots = statSlots.map((v, k) => (v === true || v === 1) ? k : -1).filter(k => k >= 0);
  const statDelivery = seededSlots.length >= 2;
  const spectatorRolesSynced = spectatorRoles.some(v => v !== null && v !== -1);

  let networkClear = false;
  let clearDetail = { seededSlots, afterRemove: [] };
  if (seededSlots.length >= 2) {
    sendServer("removebot");
    for (let i = 0; i < 12; i += 1) {
      await delay(3_000);
      const after = await statValids();
      const cleared = seededSlots.filter(k => !(after[k] === true || after[k] === 1));
      const kept = seededSlots.filter(k => after[k] === true || after[k] === 1);
      clearDetail = { seededSlots, afterRemove: after, cleared, kept, t: (i + 1) * 3 };
      if (cleared.length === 1 && kept.length >= 1) { networkClear = true; break; }
    }
  }

  // --- Phase 3: local receiver round-trip (deterministic fallback) -----------
  // The network phase above already exercises both receivers end-to-end; this
  // direct local run is the fallback when the environment cannot produce
  // spectator stats (e.g. no bots available).
  await tool("run_script", { instance: 1, script: "uh_ti_stat", args: [0, 1, 0, 0], always: true }, 12_000);
  await delay(1_000);
  const localStat = await mapArray("uhtistatvalid", 0);
  await tool("run_script", { instance: 1, script: "uh_ti_stat_clear", args: [0], always: true }, 12_000);
  await delay(1_000);
  const localClear = await mapArray("uhtistatvalid", 0);
  const receiverRoundTrip = (localStat === true || localStat === 1) && (localClear === false || localClear === 0);

  // --- Phase 4: join; prove the joining player's OWN status/life snapshot ----
  // 0 / -1 are the client defaults, so perturb uhtiova/uhtiovatarget to a
  // sentinel first; the join's ENTER snapshot must actively overwrite them.
  await tool("set_map_var", { instance: 1, name: "uhtiova", value: 7 }, 8_000);
  await tool("set_map_var", { instance: 1, name: "uhtiovatarget", value: 7 }, 8_000);
  const ovaSentinel = { ova: await mapVar("uhtiova"), target: await mapVar("uhtiovatarget") };

  // Capture the pre-join role/life, then sentinel every still-NULL slot.  The
  // bots' slots are already valid, so requiring a sentineled slot to become a
  // valid uhtirole AND uhtilife proves the join wrote the joining player's own
  // row rather than merely re-observing a bot row.
  const preJoinRole = [];
  const preJoinLife = [];
  for (let k = 0; k < STAT_SLOTS; k += 1) { preJoinRole.push(await mapArray("uhtirole", k)); preJoinLife.push(await mapArray("uhtilife", k)); }
  const sentinelSlots = [];
  for (let k = 0; k < STAT_SLOTS; k += 1) {
    if (preJoinRole[k] === null || preJoinRole[k] === -1) {
      await tool("set_map_array", { instance: 1, name: "uhtirole", index: k, value: -7 }, 8_000);
      await tool("set_map_array", { instance: 1, name: "uhtilife", index: k, value: -7 }, 8_000);
      sentinelSlots.push(k);
    }
  }

  const joinOut = await tool("run_command", { instance: 1, text: "join" }, 15_000).then(text);
  let after = null;
  let selfSlot = -1;
  for (let i = 0; i < 20; i += 1) {
    await delay(6_000);
    after = await roleSnapshot();
    selfSlot = -1;
    for (const k of sentinelSlots) {
      const role = after.role[k];
      const life = after.life[k];
      if (role !== null && role !== -1 && role !== -7
          && life !== null && life !== -1 && life !== -7) { selfSlot = k; break; }
    }
    if (selfSlot >= 0 && after.policy !== null && after.policy !== -1) break;
  }
  const joinSnapshot = after && after.policy !== null && after.policy !== -1 && selfSlot >= 0;
  let ovaDelivery = false;
  for (let i = 0; i < 12; i += 1) {
    const ova = await mapVar("uhtiova");
    const target = await mapVar("uhtiovatarget");
    if (ova === 0 && target === -1) { ovaDelivery = true; break; }
    await delay(3_000);
  }
  const ovaSentinelSet = ovaSentinel.ova === 7 && ovaSentinel.target === 7;
  const ovaDelivered = ovaSentinelSet && ovaDelivery;

  let actorClass = "";
  try {
    const actor = await tool("actor_state", { instance: 1 }, 12_000);
    actorClass = (actor.structuredContent || {}).class || (text(actor).match(/"class"\s*:\s*"([^"]+)"/) || [])[1] || "";
  } catch { /* a spectator has no actor */ }

  const stress = [];
  if (options.stress) {
    if (!(spectatorHello && spectatorRolesSynced && ovaDelivered && joinSnapshot && statDelivery && networkClear)) {
      throw new Error("basic network delivery must pass before the load test");
    }
    const { parseAcsProfile } = await import(pathToFileURL(join(MCP_DIR, "dist/parsers/acsprofile.js")));
    // Dedicated-server bridge commands print to stdout but may not complete
    // the bridge response. Read their real console output instead.
    const serverCommand = async (line, pattern, timeoutMs = 5_000) => {
      const start = readFileSync(SERVER_LOG, "utf8").length;
      sendServer(line);
      for (let i = 0; i < timeoutMs / 100; i++) {
        await delay(100);
        if (dedicated.exitCode !== null) throw new Error("server exited during " + line);
        const out = readFileSync(SERVER_LOG, "utf8").slice(start);
        const match = out.match(pattern);
        if (match) return { out, match };
      }
      throw new Error("server console response timed out: " + line);
    };
    const serverArray = async (name, index) => {
      const { match } = await serverCommand(`getmaparray ${name} ${index}`, new RegExp(`maparray ${name}\\[${index}\\] = (-?\\d+)`));
      return Number(match[1]);
    };
    const connectedSlots = async () => {
      const slots = [];
      for (let i = 0; i < 64; i++) {
        if (await serverArray("uhsrvHelloSeen", i)) slots.push(i);
      }
      return slots;
    };
    const checkLoad = async (label, expected) => {
      await delay(2_000);
      let slots = await connectedSlots();
      for (let i = 0; i < 4 && slots.length !== expected; i++) {
        await delay(2_000);
        slots = await connectedSlots();
      }
      if (slots.length !== expected) throw new Error(`${label}: expected ${expected} connected slots, got ${slots.length}`);
      // Include first-time identity resolution and all-client snapshot bursts
      // in the measured window, rather than measuring only the warm cache.
      sendServer("acsprofile clear");
      await delay(300);
      sendServer("pukename ub_StartUpSettings");
      await delay(3_000);
      const pending = [];
      for (const pn of slots) pending.push(await serverArray("uhsrvSnapshotRows", pn));
      const { out } = await serverCommand("acsprofile max 0", /All functions:/);
      const watch = parseAcsProfile(out.split(/\r?\n/)).find(r => r.section === "script" && r.module.toLowerCase() === "unholy" && r.name.includes("uh_ti_serverwatch"));
      const errors = /Runaway|Bad script definition|VM execution aborted|ACS execution error/i.test(readFileSync(SERVER_LOG, "utf8"));
      const pass = !!watch && watch.runs > 0 && watch.max > 0 && watch.max < 2_000_000
        && pending.every(n => n === 0) && !errors;
      stress.push({ label, pass, connected: slots.length, snapshotsDrained: pending.every(n => n === 0), watch });
      if (!pass) throw new Error(`${label}: script budget/snapshot failure: ${JSON.stringify(stress.at(-1))}`);
    };
    // Keep the real client as a spectator so it can verify the highest slot's
    // authorized stats and identity over the network.
    await tool("run_command", { instance: 1, text: "spectate" }, 15_000);
    await delay(2_000);
    // Hold the LMS countdown so bot combat cannot end a round or change maps
    // mid-measurement. sv_minplayers is not an LMS start gate in this engine.
    sendServer("sv_lmscountdowntime 3600");
    await delay(300);
    sendServer("map " + (profileData.map || "MM2DW1"));
    await delay(12_000);
    let count = (await connectedSlots()).length;
    for (const target of [33, 64]) {
      while (count < target) {
        sendServer("addbot");
        await delay(250);
        count++;
      }
      await checkLoad(`${target} slots`, target);
    }
    // Re-enter a populated map, exercising OPEN hello for every connected
    // slot. The profile assertion also ensures the watch survives that burst.
    // changemap includes an intermission; wait for the actual new level, not
    // a fixed sleep that can sample half of each map's arrays.
    await serverCommand("changemap " + (profileData.map || "MM2DW1"), /\*\*\* [A-Z0-9]+:/, 30_000);
    await delay(2_000);
    await checkLoad("64 slots after map reload", 64);
    await tool("run_command", { instance: 1, text: "disconnect" }, 15_000);
    await delay(2_000);
    await tool("run_command", { instance: 1, text: "connect 127.0.0.1:" + options.gamePort }, 25_000);
    await delay(8_000);
    await checkLoad("64 slots after spectator reconnect", 64);
    const highRole = await mapArray("uhtirole", 63);
    const highStat = await mapArray("uhtistatvalid", 63);
    const pass = highRole !== null && highRole !== -1 && (highStat === true || highStat === 1);
    stress.push({ label: "remote slot 63 delivery", pass, role: highRole, stats: highStat });
    if (!pass) throw new Error(`highest slot delivery failed: role=${highRole}, stats=${highStat}`);
  }

  const log = readFileSync(SERVER_LOG, "utf8");
  // Every receiver must be proven over the network.  The local receiver
  // round-trip is a diagnostic only: it must never stand in for network
  // delivery, or a broken sender could still let the gate pass.
  const clearVerified = networkClear;
  const pass = spectatorHello && spectatorRolesSynced && ovaDelivered
    && joinSnapshot && statDelivery && networkClear && stress.every(r => r.pass);
  result = {
    status: pass ? "pass" : "fail",
    profile: options.profile,
    stress,
    gamePort: options.gamePort,
    phases: {
      spectatorHello: { pass: spectatorHello, snapshot: spectator },
      spectatorRoles: { pass: spectatorRolesSynced, roles: spectatorRoles },
      spectatorStatClear: { pass: networkClear, statDelivery, detail: clearDetail },
      ovaDelivery: { pass: ovaDelivered, sentinel: ovaSentinel, sentinelSet: ovaSentinelSet, redelivered: ovaDelivery },
      localReceiver: { pass: receiverRoundTrip, set: localStat, cleared: localClear },
      joinSnapshot: { pass: joinSnapshot, selfSlot, sentinelSlots, preJoinRole, preJoinLife, snapshot: after },
    },
    pass,
    spectatorHello,
    spectatorRolesSynced,
    joinSnapshot,
    selfSlot,
    ovaDelivered,
    ovaSentinelSet,
    ovaDelivery,
    statDelivery,
    networkClear,
    receiverRoundTrip,
    clearVerified,
    actorClass,
    connectOutput: connectOut,
    joinOutput: joinOut,
    serverEntered: [...log.matchAll(/(\w+) (?:entered|joined) the game\./g)].map(m => m[0]).slice(0, 12),
    serverLog: SERVER_LOG,
    serverLogTail: log.split(/\r?\n/).slice(-12),
  };
} catch (error) {
  result = { status: "error", error: error instanceof Error ? error.message : String(error), serverStderr: stderr, serverLog: SERVER_LOG, serverLogTail: dedicatedLog.split(/\r?\n/).slice(-20) };
} finally {
  for (const instance of launched.reverse()) { try { await tool("kill_instance", { instance }, 15_000); } catch { /* best effort */ } }
  if (dedicated && dedicated.exitCode === null) {
    dedicated.kill("SIGTERM");
    await Promise.race([new Promise(r => dedicated.once("exit", r)), delay(4_000)]);
    if (dedicated.exitCode === null) dedicated.kill("SIGKILL");
  }
  await client.close().catch(() => {});
  if (isolatedRoot) rmSync(isolatedRoot, { recursive: true, force: true });
}
console.log(options.json ? JSON.stringify(result) : JSON.stringify(result, null, 2));
process.exitCode = result.status === "pass" ? 0 : 1;
