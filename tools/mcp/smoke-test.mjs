#!/usr/bin/env node

import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { launchInstanceArgs, loadResolvedProfile } from "../resolve-launch-profile.mjs";

const PROJECT_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const DEFAULT_PROFILE = join(PROJECT_ROOT, "tools/mm8bdm-v6b.launch.json");
const SERVER_RUNNER = join(PROJECT_ROOT, "tools/mcp/server-runner.mjs");

function usage() {
  return `Usage: smoke-test.sh [options]

Launch one named Linux Zandronum MCP profile, collect a compact startup summary
and player state, then quit the instance cleanly.

Options:
  --profile NAME       launch profile (default: mm8bdm-v6b-smoke)
  --instance N         MCP instance number (default: 1)
  --timeout-sec N      per-request timeout (default: 90)
  --json               emit one machine-readable JSON object
  --dry-run            validate paths and print the resolved configuration only
  --help               show this help

Environment overrides:
  ZANDRONUM_NODE, ZANDRONUM_MCP_DIR, ZANDRONUM_MCP_SERVER,
  ZANDRONUM_EXE, ZANDRONUM_LAUNCH_PROFILES, ZANDRONUM_BRIDGE_PORT
`;
}

function parsePositiveInt(value, flag) {
  const n = Number.parseInt(value, 10);
  if (!Number.isInteger(n) || n <= 0) throw new Error(`${flag} expects a positive integer`);
  return n;
}

function parseArgs(argv) {
  const options = {
    profile: "mm8bdm-v6b-smoke",
    instance: 1,
    timeoutSec: 90,
    json: false,
    dryRun: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      console.log(usage());
      process.exit(0);
    }
    if (arg === "--json") {
      options.json = true;
      continue;
    }
    if (arg === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (arg === "--profile") {
      options.profile = argv[++i];
      if (!options.profile) throw new Error("--profile expects a name");
      continue;
    }
    if (arg === "--instance") {
      options.instance = parsePositiveInt(argv[++i], "--instance");
      continue;
    }
    if (arg === "--timeout-sec") {
      options.timeoutSec = parsePositiveInt(argv[++i], "--timeout-sec");
      continue;
    }
    throw new Error(`unknown option ${arg} (use --help)`);
  }
  return options;
}

function runtimeConfig() {
  const mcpDir = process.env.ZANDRONUM_MCP_DIR;
  if (!mcpDir) throw new Error("set ZANDRONUM_MCP_DIR to your ZandronumMCP checkout");
  const engine = process.env.ZANDRONUM_EXE;
  if (!engine) throw new Error("set ZANDRONUM_EXE to the bridge-patched Zandronum binary");
  const profileFile = process.env.ZANDRONUM_LAUNCH_PROFILES || DEFAULT_PROFILE;
  return {
    node: process.env.ZANDRONUM_NODE || process.execPath,
    mcpDir,
    server: process.env.ZANDRONUM_MCP_SERVER || join(mcpDir, "dist/server.js"),
    engine,
    profileFile: resolve(profileFile),
    bridgePort: process.env.ZANDRONUM_BRIDGE_PORT || "7777",
  };
}

function loadProfile(config, name) {
  if (!existsSync(config.profileFile)) {
    throw new Error(`launch profile file not found: ${config.profileFile}`);
  }
  try {
    return loadResolvedProfile(PROJECT_ROOT, config.profileFile, name);
  } catch (error) {
    throw new Error(`invalid launch profile file ${config.profileFile}: ${error.message}`);
  }
}

function firstLine(value) {
  return String(value || "").split(/\r?\n/, 1)[0] || "(empty)";
}

function textFromResult(result) {
  return (result?.content ?? [])
    .filter((item) => item?.type === "text")
    .map((item) => item.text)
    .join("\n")
    .trim();
}

function summarizeStartup(text) {
  const match = text.match(/Detected (\d+) error line/);
  const reportedLines = match ? Number.parseInt(match[1], 10) : 0;
  return {
    reportedLines,
    noCompileOrFatal: /No compile\/fatal errors detected/i.test(text),
    summary: firstLine(text),
  };
}

function tail(value, max = 1600) {
  const text = String(value || "");
  return text.length <= max ? text : `…${text.slice(-max)}`;
}

async function callTool(client, name, args, timeoutMs) {
  const result = await client.callTool({ name, arguments: args }, undefined, { timeout: timeoutMs });
  if (!result) throw new Error(`${name}: MCP returned no result`);
  if (result.isError) {
    const error = new Error(`${name}: ${textFromResult(result) || "tool returned an error"}`);
    error.toolResult = result;
    throw error;
  }
  return result;
}

function dryRun(options, config, selected) {
  return {
    status: "dry-run",
    profile: options.profile,
    instance: options.instance,
    node: config.node,
    server: config.server,
    cwd: config.mcpDir,
    engine: config.engine,
    launchProfiles: config.profileFile,
    bridgePort: config.bridgePort,
    referencedFiles: selected.files,
  };
}

function printResult(result, json) {
  if (json) {
    console.log(JSON.stringify(result));
    return;
  }
  if (result.status === "ok") {
    console.log(`status=ok profile=${result.profile} instance=${result.instance}`);
    console.log(`launch=${result.launch}`);
    console.log(
      `startup_reported_lines=${result.startup.reportedLines} no_compile_or_fatal=${result.startup.noCompileOrFatal}`,
    );
    console.log(`player_state=${JSON.stringify(result.playerState)}`);
    console.log(`cleanup=${result.cleanup}`);
    return;
  }
  if (result.status === "dry-run") {
    console.log(`status=dry-run profile=${result.profile} instance=${result.instance}`);
    console.log(`node=${result.node}`);
    console.log(`server=${result.server}`);
    console.log(`cwd=${result.cwd}`);
    console.log(`engine=${result.engine}`);
    console.log(`launch_profiles=${result.launchProfiles}`);
    console.log(`referenced_files=${result.referencedFiles.length}`);
    return;
  }
  console.error(`status=error profile=${result.profile ?? "unknown"}`);
  console.error(`error=${result.error}`);
  if (result.toolDetail) console.error(`tool_detail=${result.toolDetail}`);
  if (result.engineLog) console.error(`engine_log=${result.engineLog}`);
  if (result.serverStderr) console.error(`server_stderr=${result.serverStderr}`);
  if (result.protocolNoise) console.error(`protocol_noise=${result.protocolNoise}`);
}

async function run(options) {
  const config = runtimeConfig();
  const selected = loadProfile(config, options.profile);
  if (!existsSync(config.node)) throw new Error(`Node executable not found: ${config.node}`);
  if (!existsSync(config.server)) throw new Error(`MCP server not found: ${config.server}`);
  if (!existsSync(config.engine)) throw new Error(`Zandronum engine not found: ${config.engine}`);
  if (options.dryRun) return dryRun(options, config, selected);

  const sdkRoot = join(config.mcpDir, "node_modules/@modelcontextprotocol/sdk/dist/esm");
  const [{ Client }, { StdioClientTransport }] = await Promise.all([
    import(pathToFileURL(join(sdkRoot, "client/index.js"))),
    import(pathToFileURL(join(sdkRoot, "client/stdio.js"))),
  ]);
  const transport = new StdioClientTransport({
    command: config.node,
    args: [SERVER_RUNNER, config.server],
    cwd: config.mcpDir,
    env: {
      ...process.env,
      ZANDRONUM_BRIDGE_PORT: config.bridgePort,
      ZANDRONUM_EXE: config.engine,
      ZANDRONUM_LAUNCH_PROFILES: config.profileFile,
    },
    stderr: "pipe",
  });
  let serverStderr = "";
  transport.stderr?.on("data", (chunk) => {
    serverStderr = tail(`${serverStderr}${chunk}`, 12000);
  });
  const client = new Client({ name: "mm8bdm-mcp-smoke", version: "1.0.0" });
  let cleanup = "not attempted";
  let connected = false;
  let outcome;
  try {
    await client.connect(transport);
    connected = true;

    const launchResult = await callTool(
      client,
      "launch_instance",
      launchInstanceArgs(options.instance, selected.profile),
      options.timeoutSec * 1000,
    );

    const startupResult = await callTool(
      client,
      "get_startup_errors",
      { instance: options.instance },
      15000,
    );
    const stateResult = await callTool(client, "player_state", { instance: options.instance }, 15000);
    const playerState = stateResult.structuredContent || (() => {
      try {
        return JSON.parse(textFromResult(stateResult));
      } catch {
        return textFromResult(stateResult);
      }
    })();

    outcome = {
      status: "ok",
      profile: options.profile,
      instance: options.instance,
      launch: firstLine(textFromResult(launchResult)),
      startup: summarizeStartup(textFromResult(startupResult)),
      playerState,
    };
  } catch (error) {
    if (error instanceof Error) {
      error.serverStderr = tail(serverStderr);
      if (connected) {
        try {
          const log = await callTool(client, "read_engine_log", { instance: options.instance, maxLines: 200 }, 15000);
          error.engineLog = tail(textFromResult(log), 8000);
        } catch (logError) {
          error.engineLog = `unavailable: ${logError.message}`;
        }
      }
    }
    throw error;
  } finally {
    if (connected) {
      try {
        const cleanupResult = await callTool(client, "kill_instance", { instance: options.instance }, 15000);
        cleanup = firstLine(textFromResult(cleanupResult));
      } catch (error) {
        cleanup = `failed: ${error.message}`;
      }
    }
    await client.close();
  }
  return { ...outcome, cleanup };
}

const options = parseArgs(process.argv.slice(2));
try {
  const result = await run(options);
  printResult(result, options.json);
} catch (error) {
  const result = {
    status: "error",
    profile: options.profile,
    instance: options.instance,
    error: error instanceof Error ? error.message : String(error),
  };
  if (error?.toolResult) result.toolDetail = tail(textFromResult(error.toolResult));
  if (error?.engineLog) result.engineLog = error.engineLog;
  if (error?.serverStderr) result.serverStderr = error.serverStderr;
  if (error?.protocolNoise) result.protocolNoise = error.protocolNoise;
  printResult(result, options.json);
  process.exitCode = 1;
}
