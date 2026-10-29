#!/usr/bin/env node
// Focused v6c weapon death regression; does not prove dedicated-server behavior.
import { mkdtempSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";
import { loadResolvedProfile, launchInstanceArgs } from "../resolve-launch-profile.mjs";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const profileFile = resolve(root, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const { profile } = loadResolvedProfile(root, profileFile, process.env.UH_WEAPON_DEATH_PROFILE || "mm8bdm-v6c-smoke");
const args = process.argv.slice(2);
if (args.length !== 2 || args[0] !== "--probe") {
  throw Error("Usage: node tools/mcp/weapon-death-test.mjs --probe PATH (see tools/README.md)");
}
profile.files.push(resolve(args[1]));
profile.map = "TRAINING";
const mcpDir = process.env.ZANDRONUM_MCP_DIR;
const engine = process.env.ZANDRONUM_EXE;
if (!mcpDir || !engine) throw Error("Set ZANDRONUM_MCP_DIR and ZANDRONUM_EXE, as for smoke-test.sh");
const sdkRoot = join(mcpDir, "node_modules/@modelcontextprotocol/sdk/dist/esm");
const [{ Client }, { StdioClientTransport }] = await Promise.all([
  import(pathToFileURL(join(sdkRoot, "client/index.js"))),
  import(pathToFileURL(join(sdkRoot, "client/stdio.js"))),
]);
const isolated = mkdtempSync(join(tmpdir(), "uh-weapon-death-"));
const transport = new StdioClientTransport({
  command: process.env.ZANDRONUM_NODE || process.execPath,
  args: [join(root, "tools/mcp/server-runner.mjs"), process.env.ZANDRONUM_MCP_SERVER || join(mcpDir, "dist/server.js")],
  cwd: isolated,
  env: { ...process.env, ZANDRONUM_LAUNCH_PROFILES: profileFile, ZANDRONUM_EXE: engine },
  stderr: "pipe",
});
transport.stderr?.on("data", chunk => process.stderr.write(chunk));
const client = new Client({ name: "uh-weapon-death-test", version: "1.0.0" });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function call(name, args = {}) {
  const result = await client.callTool(
    { name, arguments: { instance: 1, ...args } }, undefined, { timeout: name === "launch_instance" ? 150000 : 55000 },
  );
  if (result.isError) throw Error(JSON.stringify(result));
  return result;
}

async function cmd(text) {
  const result = await call("run_command", { text });
  console.log(text, JSON.stringify(result.content));
}


async function actor() { return (await call("actor_state")).structuredContent; }
function check(ok, message) { if (!ok) throw Error(message); }
try {
 await client.connect(transport);
 await call("launch_instance", launchInstanceArgs(1, profile,
   [...profile.extraArgs, "-config", join(isolated, "engine.ini"), "+playerclass", "Igniter"]));
 const cases = [
  ["Igniter", "Igniter_W"],
  ["Juggernaut", "Juggernaut_W"],
  ["Igniter", "MagicDevilEye_W"],
 ];
 for (const [cls, weapon] of cases) {
  await cmd(`playerclass ${cls}`);
  await cmd("map TRAINING");
  await call("set_pause", {paused:false});
  await delay(1300);
  if (weapon === "MagicDevilEye_W") {
    await cmd("pukename rz_debug_MorphMe 0 115"); await delay(800);
  }
  let before = await actor();
  check(before.weapon === weapon, `Weapon setup failed: expected ${weapon}, got ${before.weapon}`);
  await cmd("pukename UHTest_WeaponDeath");
  await delay(250);
  const dead = await actor();
  check(dead.health <= 0, `Lethal hit did not kill ${weapon}`);
  await delay(900);
  await call("player_state");
  console.log(JSON.stringify({case:weapon, health:dead.health, status:"pass"}));
 }
 console.log(JSON.stringify({status:"pass", cases:cases.length}));
} catch (e) {
 console.error(String(e)); process.exitCode=1;
 try { console.error(JSON.stringify(await call("read_engine_log", {maxLines:200}))); } catch {}
} finally {
 try { await call("kill_instance"); } catch {}
 await client.close(); rmSync(isolated, {recursive:true,force:true});
}
