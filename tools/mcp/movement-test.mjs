#!/usr/bin/env node
// Focused v6c movement contracts and real input hook dispatch. Offline only.
import { mkdtempSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";
import { loadResolvedProfile, launchInstanceArgs } from "../resolve-launch-profile.mjs";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const profileFile = resolve(root, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const { profile } = loadResolvedProfile(root, profileFile, process.env.UH_MOVEMENT_PROFILE || "mm8bdm-v6c-smoke");
const args = process.argv.slice(2);
if (args.length !== 2 || args[0] !== "--probe") {
  throw Error("Usage: node tools/mcp/movement-test.mjs --probe PATH (see tools/README.md)");
}
profile.files.push(resolve(args[1]));
profile.map = "MM2DW1";
const mcpDir = process.env.ZANDRONUM_MCP_DIR;
const engine = process.env.ZANDRONUM_EXE;
if (!mcpDir || !engine) throw Error("Set ZANDRONUM_MCP_DIR and ZANDRONUM_EXE, as for smoke-test.sh");
const sdkRoot = join(mcpDir, "node_modules/@modelcontextprotocol/sdk/dist/esm");
const [{ Client }, { StdioClientTransport }] = await Promise.all([
  import(pathToFileURL(join(sdkRoot, "client/index.js"))),
  import(pathToFileURL(join(sdkRoot, "client/stdio.js"))),
]);
const isolated = mkdtempSync(join(tmpdir(), "uh-movement-"));
const transport = new StdioClientTransport({
  command: process.env.ZANDRONUM_NODE || process.execPath,
  args: [join(root, "tools/mcp/server-runner.mjs"), process.env.ZANDRONUM_MCP_SERVER || join(mcpDir, "dist/server.js")],
  cwd: isolated,
  env: { ...process.env, ZANDRONUM_LAUNCH_PROFILES: profileFile, ZANDRONUM_EXE: engine },
  stderr: "pipe",
});
transport.stderr?.on("data", chunk => process.stderr.write(chunk));
const client = new Client({ name: "uh-movement-test", version: "1.0.0" });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function call(name, args = {}) {
  const result = await client.callTool(
    { name, arguments: { instance: 1, ...args } }, undefined, { timeout: 55000 },
  );
  if (result.isError) throw Error(JSON.stringify(result));
  return result;
}

async function cmd(text) {
  const result = await call("run_command", { text });
  console.log(text, JSON.stringify(result.content));
}


function check(ok, message) { if (!ok) throw Error(message); }
try {
 await client.connect(transport);
 await call("launch_instance", launchInstanceArgs(1, profile,
   [...profile.extraArgs, "-config", join(isolated, "engine.ini"), "+playerclass", "Igniter"]));
 await call("set_pause", {paused:false});
 await delay(1500);
 await cmd("pukename UHTest_MovementContracts");
 await delay(200);
 let log = JSON.stringify(await call("read_engine_log", {cursor:0, maxLines:1000}));
 check(/UH_MOVEMENT_CONTRACTS checks=\d+ failures=0/.test(log), `Movement contracts failed: ${log}`);
 await cmd("pukename UHTest_MovementConsume 1");
 await delay(100);
 await cmd("+jump"); await delay(200);
 await cmd("-jump"); await delay(200);
 await cmd("pukename UHTest_MovementEvents"); await delay(100);
 log = JSON.stringify(await call("read_engine_log", {cursor:0, maxLines:1000}));
 const event = /UH_MOVEMENT_EVENTS any=(\d+) pressed=(\d+) held=(\d+) released=(\d+) idle=(\d+) used=(\d+)/.exec(log);
 check(event && event.slice(1,6).every(n => Number(n)>0) && event[6]==="1", `Hook event dispatch failed: ${log}`);
 console.log(event[0]);
 await cmd("pukename UHTest_MovementInputSetup");
 await cmd("+jump"); await delay(150);
 await cmd("-jump"); await delay(100);
 await cmd("pukename UHTest_MovementInputResult"); await delay(100);
 log = JSON.stringify(await call("read_engine_log", {cursor:0, maxLines:1000}));
 const airInput = /UH_MOVEMENT_INPUT airused=(\d+) velz=(-?[\d.]+)/.exec(log);
 check(airInput && airInput[1] === "1" && Number(airInput[2]) === 12, `Real input airjump failed: ${log}`);
 console.log(airInput[0]);
 await cmd("pukename rz_debug_MorphMe 0 24"); await delay(700);
 await cmd("pukename UHTest_MovementBoss"); await delay(200);
 log = JSON.stringify(await call("read_engine_log", {cursor:0, maxLines:1000}));
 check(/UH_MOVEMENT_BOSS checks=\d+ failures=0/.test(log), `Boss movement contracts failed: ${log}`);
 check(!/UH_MOVEMENT_FAIL /.test(log), "A movement assertion failed");
 check(!/ACS:|Runaway script|VM execution aborted/.test(log), "ACS runtime error during movement test");
 console.log(log.match(/UH_MOVEMENT_CONTRACTS checks=\d+ failures=0/)[0]);
 console.log(log.match(/UH_MOVEMENT_BOSS checks=\d+ failures=0/)[0]);
 console.log(JSON.stringify({status:"pass"}));
} catch (e) {
 console.error(String(e)); process.exitCode=1;
 try { console.error(JSON.stringify(await call("read_engine_log", {maxLines:200}))); } catch {}
} finally {
 try { await call("kill_instance"); } catch {}
 await client.close(); rmSync(isolated, {recursive:true,force:true});
}
