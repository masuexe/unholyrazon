#!/usr/bin/env node

import { spawn } from "node:child_process";
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { launchInstanceArgs, loadResolvedProfile } from "../resolve-launch-profile.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const PROFILES = resolve(ROOT, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const RUNNER = join(ROOT, "tools/mcp/server-runner.mjs");

function usage() {
  return `Usage: boss-ammo-test.mjs --probe PATH [--profile NAME] [--game-port N] [--json] [--dry-run]

Run the CXAirMan ammo regression with a dedicated server and one remote client.
Build --probe from fixtures/boss-ammo-probe.acs; see tools/README.md.
`;
}

const options = { profile: "mm8bdm-v6c-smoke", port: 10756, probe: "", json: false, dryRun: false };
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === "--help" || arg === "-h") { console.log(usage()); process.exit(0); }
  if (arg === "--json") { options.json = true; continue; }
  if (arg === "--dry-run") { options.dryRun = true; continue; }
  if (arg === "--probe") { options.probe = resolve(process.argv[++i]); continue; }
  if (arg === "--profile") { options.profile = process.argv[++i] || ""; continue; }
  if (arg === "--game-port") { options.port = Number.parseInt(process.argv[++i], 10); continue; }
  throw new Error(`unknown option ${arg}`);
}
if (!options.profile || !Number.isInteger(options.port) || options.port < 1024 || options.port > 65535) throw new Error("invalid options");
if (!options.probe || !existsSync(options.probe)) throw Error("--probe must name the compiled diagnostic addon");
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
const client = new Client({ name: "unholy-network-test", version: "1.0.0" });
const launched = [];
let dedicated;
let dedicatedLog = "";
let isolatedRoot;
const text = result => (result.content || []).filter(x => x.type === "text").map(x => x.text).join("\n");
async function tool(name, args, timeout = 150_000) {
  const result = await client.callTool({ name, arguments: args }, undefined, { timeout });
  if (result.isError) throw new Error(`${name}: ${text(result)}`);
  return result;
}
const common = ["-nosound", "+set", "vid_renderer", "0", "+set", "fullscreen", "0"];
let result;
try {
  await client.connect(transport);
  const { profile: profileData } = loadResolvedProfile(ROOT, PROFILES, options.profile);
  profileData.files.push(options.probe);
  // Bring up the bridge-controlled client before the dedicated process. The
  // patched engine's global SDL/network initialization is reliable in this
  // order when several copies share one Linux session.
  launched.push(1);
  await tool("launch_instance", launchInstanceArgs(1, profileData, [...(profileData.extraArgs || []), ...common, "-port", String(options.port + 1), "+name", "BatchDClient1"]));

  isolatedRoot = mkdtempSync(join(tmpdir(), "unholy-network-"));
  const serverDir = join(isolatedRoot, "server");
  cpSync(dirname(ENGINE), serverDir, { recursive: true });
  const serverEngine = join(serverDir, "zandronum");
  const serverArgs = ["-stdout", "-iwad", profileData.iwad, "-file", ...(profileData.files || []), "-host", "8", "-port", String(options.port), "+set", "sv_cheats", "1", "-deathmatch", "+map", profileData.map || "MM2DW1", ...common, "+set", "sv_updatemaster", "0", "+set", "sv_noplayertimeout", "1"];
  dedicated = spawn(serverEngine, serverArgs, { cwd: serverDir, env: { ...process.env, SDL_VIDEODRIVER: "offscreen", ZANDRONUM_BRIDGE_PORT: String(options.port + 100) }, stdio: ["pipe", "pipe", "pipe"] });
  for (const stream of [dedicated.stdout, dedicated.stderr]) stream.on("data", chunk => { dedicatedLog = `${dedicatedLog}${chunk}`.slice(-400000); });
  await new Promise(resolveDelay => setTimeout(resolveDelay, 30_000));
  if (dedicated.exitCode !== null) throw new Error(`dedicated server exited early with code ${dedicated.exitCode}`);
  const connected = await tool("run_command", { instance: 1, text: `connect 127.0.0.1:${options.port}` }, 15_000);


  let firstClientLog = "";
  for (let attempt = 0; attempt < 30; attempt += 1) {
    firstClientLog = await tool("read_engine_log", { instance: 1, cursor: 0, maxLines: 1000 }, 15_000).then(text);
    if (/Level authenticated![\s\S]*Snapshot received\./i.test(firstClientLog)) break;
    await new Promise(resolveDelay => setTimeout(resolveDelay, 2000));
  }
  const firstAuthenticated = /Level authenticated![\s\S]*Snapshot received\./i.test(firstClientLog);
  if (!firstAuthenticated) throw new Error("MCP client did not authenticate and receive a snapshot within 60 seconds");

  const delay = ms => new Promise(r => setTimeout(r, ms));
  const cmd = text => tool("run_command", {instance:1, text});
  await cmd("join"); await delay(1500);
  await cmd("pukename rz_debug_MorphMe 0 101"); await delay(1500);
  dedicated.stdin.write("pukename UHAmmoProbe 1\n"); await delay(1000);
  await tool("run_script", {instance:1,script:"UHAmmoDrift",args:[],always:true}); await delay(200);
  const snap = async label => {
    const r = await tool("actor_state", {instance:1});
    const d = r.structuredContent;
    console.log(label, JSON.stringify({class:d.class,weapon:d.weapon,inventory:d.inventory.filter(i=>/UnholyPower1500|UnholyBossAmmo200/.test(i.class))}));
    return d;
  };
  const amount = (d, item) => d.inventory.find(i => i.class === item)?.amount ?? 0;
  const check = (ok, label) => { if (!ok) throw Error(label); };
  const before = await snap("before");
  check(before.class === "CXAirMan" && before.weapon === "CXAirMan_W", "Boss setup failed");
  check(amount(before, "UnholyPower1500") === 1499, "Client drift injection failed");
  await cmd("+altattack"); await delay(5500); await cmd("-altattack");
  const after = await snap("after");
  check(amount(after, "UnholyPower1500") === 0, "Remote ultimate meter did not clear");
  await delay(600);
  await cmd("+altattack"); await delay(500); await cmd("-altattack");
  check(amount(await snap("insufficient"), "UnholyPower1500") === 0, "Insufficient meter changed");
  dedicated.stdin.write("pukename UHAmmoProbe 1\n"); await delay(600);
  check(amount(await snap("refilled"), "UnholyPower1500") === 1500, "Refill failed");
  await cmd("+altattack"); await delay(5500); await cmd("-altattack");
  check(amount(await snap("normal cast"), "UnholyPower1500") === 0, "Normal cast failed");
  await delay(700);
  await cmd("+reload"); await delay(250); await cmd("-reload");
  check(amount(await snap("reload spent"), "UnholyBossAmmo200") === 0, "Teleport meter did not clear");
  await delay(3000);
  check(amount(await snap("reload recovered"), "UnholyBossAmmo200") === 200, "Teleport meter did not recover");
  dedicated.stdin.write("pukename UHAmmoProbe 0\n"); await delay(300);
  check(/AMMOPROBE server power=0/.test(dedicatedLog), "Server meter did not clear");
  result = {status:"pass", serverLogTail:dedicatedLog.slice(-1500)};

} catch (error) {
  result = { status: "error", error: error instanceof Error ? error.message : String(error), serverStderr: stderr };
} finally {
  for (const instance of launched.reverse()) {
    try { await tool("kill_instance", { instance }, 15_000); } catch { /* cleanup best effort */ }
  }
  if (dedicated?.exitCode === null) {
    dedicated.kill("SIGTERM");
    await Promise.race([new Promise(resolveExit => dedicated.once("exit", resolveExit)), new Promise(resolveDelay => setTimeout(resolveDelay, 3000))]);
    if (dedicated.exitCode === null) dedicated.kill("SIGKILL");
  }
  await client.close();
  if (isolatedRoot) rmSync(isolatedRoot, { recursive: true, force: true });
}
console.log(options.json ? JSON.stringify(result) : JSON.stringify(result, null, 2));
process.exitCode = result.status === "pass" ? 0 : 1;
