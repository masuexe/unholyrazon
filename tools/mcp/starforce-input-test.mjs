#!/usr/bin/env node
// Focused local input regression; does not prove dedicated-server delivery.
import { mkdtempSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";
import { loadResolvedProfile, launchInstanceArgs } from "../resolve-launch-profile.mjs";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const profileFile = join(root, "tools/mm8bdm-v6b.launch.json");
const { profile } = loadResolvedProfile(root, profileFile, "mm8bdm-v6b-smoke");
const args = process.argv.slice(2);
if (args.length && (args.length !== 2 || args[0] !== "--pk3")) {
  throw Error("Usage: node tools/mcp/starforce-input-test.mjs [--pk3 PATH]");
}
if (args.length) profile.files[profile.files.length - 1] = resolve(args[1]);
const mcpDir = process.env.ZANDRONUM_MCP_DIR;
const engine = process.env.ZANDRONUM_EXE;
if (!mcpDir || !engine) throw Error("Set ZANDRONUM_MCP_DIR and ZANDRONUM_EXE, as for smoke-test.sh");
const sdkRoot = join(mcpDir, "node_modules/@modelcontextprotocol/sdk/dist/esm");
const [{ Client }, { StdioClientTransport }] = await Promise.all([
  import(pathToFileURL(join(sdkRoot, "client/index.js"))),
  import(pathToFileURL(join(sdkRoot, "client/stdio.js"))),
]);
const isolated = mkdtempSync(join(tmpdir(), "uh-starforce-input-"));
const transport = new StdioClientTransport({
  command: process.env.ZANDRONUM_NODE || process.execPath,
  args: [join(root, "tools/mcp/server-runner.mjs"), process.env.ZANDRONUM_MCP_SERVER || join(mcpDir, "dist/server.js")],
  cwd: isolated,
  env: { ...process.env, ZANDRONUM_LAUNCH_PROFILES: profileFile, ZANDRONUM_EXE: engine },
  stderr: "pipe",
});
transport.stderr?.on("data", chunk => process.stderr.write(chunk));
const client = new Client({ name: "uh-starforce-input-test", version: "1.0.0" });
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

async function state(label) {
  const result = await call("actor_state");
  const actor = result.structuredContent;
  console.log(label, JSON.stringify({
    class: actor.class,
    weapon: actor.weapon,
    inv: actor.inventory.filter(item =>
      /^(SF_CardQ|WarRockStelar.*_W$|WR_|UnholyBossAmmo250|SF_CanLockOn)/.test(item.class)),
  }));
  return actor;
}

try{
 await client.connect(transport);
 console.log(JSON.stringify(await call('launch_instance', launchInstanceArgs(1, profile,
   [...profile.extraArgs, '-config', join(isolated, 'engine.ini'), '+playerclass', 'RedWarrior']))));
 await call('set_pause',{paused:false});await delay(1500);
 await cmd('pukename rz_debug_MorphMe 0 51');await delay(500);
 const main='WarRockStelar_Control_W';
 const amount=(d,n)=>d.inventory.find(x=>x.class===n)?.amount??0;
 const queue=d=>Array.from({length:6},(_,i)=>amount(d,'SF_CardQ'+i));
 const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
 let d=await state('morphed');assert(d.class.toLowerCase()==='warrockstelar'&&d.weapon===main,'Boss setup failed');
 await cmd('give UnholyBossAmmo250 250');await cmd('weapprev');await delay(300);
 d=await state('draw');assert(d.weapon===main&&queue(d).every(x=>x>0),'Draw or return failed');
 assert(!amount(d,'WR_LockOnFlag'),'Draw changed lock');
 await cmd('give SF_CanLockOn');await delay(300);await cmd('weapnext');await delay(300);
 d=await state('lock on');assert(d.weapon===main&&amount(d,'WR_LockOnFlag')===1,'Lock on failed');
 await cmd('weapnext');await delay(300);d=await state('lock off');assert(!amount(d,'WR_LockOnFlag'),'Lock off failed');
 await cmd('give SF_CanLockOn');await cmd(Array(12).fill('weapnext').join('; '));await delay(300);
 d=await state('lock burst');assert(amount(d,'WR_LockOnFlag')===1&&d.weapon===main,'Lock burst flipped or stuck');
 await cmd('weapnext');await delay(300);
 await cmd('give UnholyBossAmmo250 250');await cmd(Array(12).fill('weapprev').join('; '));await delay(300);
 d=await state('draw burst');assert(!amount(d,'WR_LockOnFlag')&&queue(d).every(x=>x>0)&&d.weapon===main,'Draw burst crossed direction');
 // Pause around a short press so even a fast card cannot chain before release.
 const before=queue(d);
 await call('set_pause', {paused:true});
 await cmd('+reload');
 await call('step', {tics:3});
 await cmd('-reload');
 d=await state('short reload');
 const afterFirst=[...before.slice(1),0];
 assert(JSON.stringify(queue(d))===JSON.stringify(afterFirst),'Short Reload did not use the first card');
 await call('step', {tics:105});
 d=await state('released reload');
 assert(JSON.stringify(queue(d))===JSON.stringify(afterFirst),'Release consumed a following card');
 await call('set_pause', {paused:false});

 // An active card cooldown must prevent the next card, even with Reload held.
 await cmd('give BattleCardDelay');
 await cmd('+reload');await delay(300);
 d=await state('card cooldown');
 assert(JSON.stringify(queue(d))===JSON.stringify(afterFirst),'Reload bypassed the card cooldown');
 await cmd('take BattleCardDelay 9999');
 // Keep the same press held: once ready it must consume the remaining hand.
 const deadline=Date.now()+20000;
 do {
  await delay(350);
  d=await state('held reload');
 } while(queue(d).some(x=>x>0) && Date.now()<deadline);
 assert(queue(d).every(x=>x===0),'Held Reload did not empty the remaining hand');
 await delay(1800);
 await cmd('give UnholyBossAmmo250 250');await delay(500);
 d=await state('empty held reload');
 assert(queue(d).every(x=>x===0)&&d.weapon===main,'Empty hand restarted or drew cards automatically');
 await cmd('-reload');await delay(300);
 for(const button of ['attack','altattack']){
  await cmd('give UnholyBossAmmo250 250');await cmd('give SF_CanLockOn');await cmd('take WR_LockOnFlag 9999');
  await cmd('+'+button);await cmd(Array(12).fill('weapprev').join('; '));await delay(200);await cmd('-'+button);await delay(1300);
  d=await state(button+' draw');assert(d.weapon===main&&!amount(d,'WR_LockOnFlag')&&queue(d).every(x=>x>0),'Combat draw crossed direction or stuck');
  await cmd('give SF_CanLockOn');await cmd('+'+button);await cmd(Array(12).fill('weapnext').join('; '));await delay(200);await cmd('-'+button);await delay(1300);
  d=await state(button+' lock');assert(d.weapon===main&&amount(d,'WR_LockOnFlag')===1,'Combat lock failed');
 }
 await cmd('weapprev; weapnext');await delay(400);await state('rapid reversal');
 console.log('PASS: boss setup, draw, lock, bursts, Reload release, cooldown gating, held six-card exhaustion, combat switching');

} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  try { await call("kill_instance"); } catch (error) {
    console.error("Engine cleanup failed:", error.message);
    process.exitCode = 1;
  }
  await client.close();
  rmSync(isolated, { recursive: true, force: true });
}
