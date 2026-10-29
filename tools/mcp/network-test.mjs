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
  return `Usage: network-test.mjs [--profile NAME] [--game-port N] [--json] [--dry-run]

Launch one local Zandronum server and two clients through a single MCP session,
connect both clients, verify their names in the authoritative server log, then
clean up all three instances.
`;
}

const options = { profile: "mm8bdm-v6c-smoke", port: 10746, json: false, dryRun: false };
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === "--help" || arg === "-h") { console.log(usage()); process.exit(0); }
  if (arg === "--json") { options.json = true; continue; }
  if (arg === "--dry-run") { options.dryRun = true; continue; }
  if (arg === "--profile") { options.profile = process.argv[++i] || ""; continue; }
  if (arg === "--game-port") { options.port = Number.parseInt(process.argv[++i], 10); continue; }
  throw new Error(`unknown option ${arg}`);
}
if (!options.profile || !Number.isInteger(options.port) || options.port < 1024 || options.port > 65535) throw new Error("invalid options");
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
let directClient;
let directClientLog = "";
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
  // Bring up the bridge-controlled client before the dedicated process. The
  // patched engine's global SDL/network initialization is reliable in this
  // order when several copies share one Linux session.
  launched.push(1);
  await tool("launch_instance", launchInstanceArgs(1, profileData, [...(profileData.extraArgs || []), ...common, "-port", String(options.port + 1), "+name", "BatchDClient1"]));

  isolatedRoot = mkdtempSync(join(tmpdir(), "unholy-network-"));
  const serverDir = join(isolatedRoot, "server");
  const directDir = join(isolatedRoot, "client2");
  cpSync(dirname(ENGINE), serverDir, { recursive: true });
  cpSync(dirname(ENGINE), directDir, { recursive: true });
  const serverEngine = join(serverDir, "zandronum");
  const directEngine = join(directDir, "zandronum");
  const serverArgs = ["-stdout", "-iwad", profileData.iwad, "-file", ...(profileData.files || []), "-host", "8", "-port", String(options.port), "-teamlms", "+map", profileData.map || "MM2DW1", ...common, "+set", "sv_updatemaster", "0", "+set", "sv_noplayertimeout", "1"];
  dedicated = spawn(serverEngine, serverArgs, { cwd: serverDir, env: { ...process.env, SDL_VIDEODRIVER: "offscreen", ZANDRONUM_BRIDGE_PORT: String(options.port + 100) }, stdio: ["ignore", "pipe", "pipe"] });
  for (const stream of [dedicated.stdout, dedicated.stderr]) stream.on("data", chunk => { dedicatedLog = `${dedicatedLog}${chunk}`.slice(-400000); });
  await new Promise(resolveDelay => setTimeout(resolveDelay, 30_000));
  if (dedicated.exitCode !== null) throw new Error(`dedicated server exited early with code ${dedicated.exitCode}`);
  const connected = await tool("run_command", { instance: 1, text: `connect 127.0.0.1:${options.port}` }, 15_000);
  const connectOutputs = [text(connected)];

  let firstClientLog = "";
  for (let attempt = 0; attempt < 30; attempt += 1) {
    firstClientLog = await tool("read_engine_log", { instance: 1, cursor: 0, maxLines: 1000 }, 15_000).then(text);
    if (/Level authenticated![\s\S]*Snapshot received\./i.test(firstClientLog)) break;
    await new Promise(resolveDelay => setTimeout(resolveDelay, 2000));
  }
  const firstAuthenticated = /Level authenticated![\s\S]*Snapshot received\./i.test(firstClientLog);
  if (!firstAuthenticated) throw new Error("MCP client did not authenticate and receive a snapshot within 60 seconds");

  const directArgs = ["-stdout", "-iwad", profileData.iwad, "-file", ...(profileData.files || []), "-port", String(options.port + 2), ...common, "+name", "BatchDClient2", "+connect", `127.0.0.1:${options.port}`];
  directClient = spawn(directEngine, directArgs, { cwd: directDir, env: { ...process.env, SDL_VIDEODRIVER: "offscreen", ZANDRONUM_BRIDGE_PORT: String(options.port + 101) }, stdio: ["ignore", "pipe", "pipe"] });
  for (const stream of [directClient.stdout, directClient.stderr]) stream.on("data", chunk => { directClientLog = `${directClientLog}${chunk}`.slice(-400000); });
  await new Promise(resolveDelay => setTimeout(resolveDelay, 45_000));
  const log = dedicatedLog;
  const names = ["BatchDClient1", "BatchDClient2"];
  const missing = names.filter(name => !log.includes(name));
  let mcpClientState;
  try {
    mcpClientState = await tool("player_state", { instance: 1 }, 15_000).then(r => r.structuredContent || text(r));
  } catch (error) {
    // A freshly connected TLMS client may still be a true spectator and have
    // no pawn. Connection/authentication is verified from both network logs.
    mcpClientState = { unavailable: error instanceof Error ? error.message : String(error) };
  }
  const states = [mcpClientState];
  const mcpClientLog = await tool("read_engine_log", { instance: 1, cursor: 0, maxLines: 1000 }, 15_000).then(text);
  const directAuthenticated = /Connected![\s\S]*Level authenticated![\s\S]*Snapshot received\./i.test(directClientLog);
  result = { status: missing.length || !directAuthenticated ? "fail" : "pass", profile: options.profile, gamePort: options.port, connectedNames: names.filter(n => !missing.includes(n)), missingNames: missing, directClientAuthenticated: directAuthenticated, connectOutputs, clientStates: states, serverLogTail: log.split(/\r?\n/).slice(-80), clientLogTails: [mcpClientLog.split(/\r?\n/).slice(-80), directClientLog.split(/\r?\n/).slice(-80)] };
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
  if (directClient?.exitCode === null) {
    directClient.kill("SIGTERM");
    await Promise.race([new Promise(resolveExit => directClient.once("exit", resolveExit)), new Promise(resolveDelay => setTimeout(resolveDelay, 3000))]);
    if (directClient.exitCode === null) directClient.kill("SIGKILL");
  }
  await client.close();
  if (isolatedRoot) rmSync(isolatedRoot, { recursive: true, force: true });
}
console.log(options.json ? JSON.stringify(result) : JSON.stringify(result, null, 2));
process.exitCode = result.status === "pass" ? 0 : 1;
