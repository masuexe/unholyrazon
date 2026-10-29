#!/usr/bin/env node
// Validate the UH countdown against the v6c CopyVision base in a real engine.
import { mkdtempSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";
import { loadResolvedProfile, launchInstanceArgs } from "../resolve-launch-profile.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
if (process.argv.length !== 4 || process.argv[2] !== "--probe") {
  throw Error("Usage: copyvision-v6c-test.mjs --probe PATH (see tools/README.md)");
}
const profileFile = resolve(root, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const { profile } = loadResolvedProfile(root, profileFile, "mm8bdm-v6c-smoke");
profile.files.push(resolve(process.argv[3]));
const mcpDir = process.env.ZANDRONUM_MCP_DIR;
if (!mcpDir || !process.env.ZANDRONUM_EXE) throw Error("Set ZANDRONUM_MCP_DIR and ZANDRONUM_EXE");
const sdk = join(mcpDir, "node_modules/@modelcontextprotocol/sdk/dist/esm");
const [{ Client }, { StdioClientTransport }] = await Promise.all([
  import(pathToFileURL(join(sdk, "client/index.js"))),
  import(pathToFileURL(join(sdk, "client/stdio.js"))),
]);
const isolated = mkdtempSync(join(tmpdir(), "uh-copyvision-v6c-"));
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [join(root, "tools/mcp/server-runner.mjs"), process.env.ZANDRONUM_MCP_SERVER || join(mcpDir, "dist/server.js")],
  cwd: isolated,
  env: { ...process.env, SDL_VIDEODRIVER: process.env.SDL_VIDEODRIVER || "offscreen", ZANDRONUM_LAUNCH_PROFILES: profileFile },
  stderr: "pipe",
});
transport.stderr?.on("data", chunk => process.stderr.write(chunk));
const client = new Client({ name: "uh-copyvision-v6c", version: "1.0.0" });
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: {instance: 1, ...args} }, undefined, { timeout: name === "launch_instance" ? 150000 : 55000 });
  if (result.isError) throw Error(JSON.stringify(result));
  return result;
}
async function value(name) {
  const result = await call("get_map_var", {name});
  if (!result.structuredContent || !Number.isInteger(result.structuredContent.value)) throw Error("Missing map variable " + name);
  return result.structuredContent.value;
}
let launched = false;
try {
  await client.connect(transport);
  launched = true;
  await call("launch_instance", launchInstanceArgs(1, profile, [...profile.extraArgs, "+playerclass", "MegaManU"]));
  await call("set_pause", {paused: false});
  await call("step", {tics: 35});
  await call("run_script", {script: "UHTest_CopyVisionLifetime", always: true});
  await call("step", {tics: 350});
  const result = { done: await value("cv_done"), checks: await value("cv_checks"), failures: await value("cv_failures") };
  console.log(JSON.stringify(result));
  if (result.done !== 1 || result.checks !== 6 || result.failures !== 0) throw Error("CopyVision lifetime regression");
} catch (error) {
  console.error(String(error)); process.exitCode = 1;
} finally {
  if (launched) { try { await call("kill_instance"); } catch (error) { console.error(String(error)); process.exitCode = 1; } }
  await client.close();
  rmSync(isolated, {recursive: true, force: true});
}
