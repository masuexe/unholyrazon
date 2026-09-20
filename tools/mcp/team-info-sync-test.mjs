#!/usr/bin/env node
//
// team-info-sync-test.mjs - runtime regression gate for the Unholy team-info
// CLIENTSIDE sync delivery (reports/unholy-team-info-and-scoreboard-icons-report.md,
// "P1 fix - per-client delivery for CLIENTSIDE receivers").
//
// Why this exists: the role/policy sync receivers (uh_ti_sync_status,
// uh_ti_sync_ova, uh_ti_sync_policy) are CLIENTSIDE scripts.  A plain
// ACS_NamedExecuteAlways call to a CLIENTSIDE script does not reach a remote
// client on a dedicated/listen server, so the client's uhtirole[] /
// uhtiscorepolicy stayed at PLS_NULL / INVALID.  This test connects a real
// remote client, has it join the game, and asserts the client's own map vars
// are populated.  It cannot be proven by static compilation.
//
// Usage:
//   node tools/mcp/team-info-sync-test.mjs [--profile NAME] [--game-port N]
//        [--bridge-port N] [--json] [--dry-run]
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
const PROFILES = process.env.ZANDRONUM_LAUNCH_PROFILES || join(ROOT, "tools/mm8bdm-v6b-linux.launch.json");
const RUNNER = join(ROOT, "tools/mcp/server-runner.mjs");
const SERVER_LOG = "/tmp/team-info-sync-server.log";

function usage() {
  return "Usage: team-info-sync-test.mjs [--profile NAME] [--game-port N] [--bridge-port N] [--json] [--dry-run]\n" +
    "\n" +
    "Launch one local Zandronum listen server plus one MCP-controlled remote client,\n" +
    "have the client join the game, then verify its local uhtirole[] / uhtilife[] /\n" +
    "uhtiscorepolicy map vars are populated by the server's per-client CLIENTSIDE\n" +
    "sync.  Requires local TCP/UDP ports and the bridge-patched engine.\n";
}

const options = { profile: "mm8bdm-v6b-smoke", gamePort: 10767, bridgePort: 7777, json: false, dryRun: false };
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === "--help" || arg === "-h") { console.log(usage()); process.exit(0); }
  if (arg === "--json") { options.json = true; continue; }
  if (arg === "--dry-run") { options.dryRun = true; continue; }
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
async function snapshot() {
  const out = { policy: await mapVar("uhtiscorepolicy"), ova: await mapVar("uhtiova"), role: [], life: [] };
  for (let k = 0; k < 4; k += 1) { out.role.push(await mapArray("uhtirole", k)); out.life.push(await mapArray("uhtilife", k)); }
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
    "-host", "8", "-port", String(options.gamePort), "-lastmanstanding",
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
  await delay(25_000);
  if (dedicated.exitCode !== null) throw new Error("listen server exited early with code " + dedicated.exitCode);

  const connectOut = await tool("run_command", { instance: 1, text: "connect 127.0.0.1:" + options.gamePort }, 25_000).then(text);
  await delay(15_000);
  const beforeJoin = await snapshot();

  // A connecting client is a true spectator; the console 'join' command makes
  // it spawn, which is what makes the mod assign a role and broadcast it.
  const joinOut = await tool("run_command", { instance: 1, text: "join" }, 15_000).then(text);
  await delay(3_000);
  if (dedicated.stdin.writable) dedicated.stdin.write("addbot\n");

  const samples = [];
  let after = null;
  for (let i = 0; i < 12; i += 1) {
    await delay(6_000);
    const sample = await snapshot();
    sample.t = (i + 1) * 6;
    samples.push(sample);
    after = sample;
    if (sample.policy !== null && sample.policy !== -1 && sample.role.some(v => v !== null && v !== -1)) break;
  }

  let actorClass = "";
  try {
    const actor = await tool("actor_state", { instance: 1 }, 12_000);
    const sc = actor.structuredContent || {};
    actorClass = sc.class || (text(actor).match(/"class"\s*:\s*"([^"]+)"/) || [])[1] || "";
  } catch { /* a spectator has no actor; leave blank */ }

  const log = readFileSync(SERVER_LOG, "utf8");
  const policy = after ? after.policy : null;
  const roles = after ? after.role : [];
  const rolesSet = roles.some(v => v !== null && v !== -1);
  const policyValid = policy !== null && policy !== -1;
  result = {
    status: policyValid && rolesSet ? "pass" : "fail",
    profile: options.profile,
    gamePort: options.gamePort,
    beforeJoin,
    afterJoin: after,
    samples,
    policyValid,
    rolesSet,
    actorClass,
    connectOutput: connectOut,
    joinOutput: joinOut,
    serverEntered: [...log.matchAll(/(\w+) (?:entered|joined) the game\./g)].map(m => m[0]).slice(0, 10),
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
