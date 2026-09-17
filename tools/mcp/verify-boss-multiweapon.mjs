#!/usr/bin/env node

import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { launchInstanceArgs, loadResolvedProfile } from "../resolve-launch-profile.mjs";

const PROJECT_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const DEFAULT_PROFILE = join(PROJECT_ROOT, "tools/mm8bdm-v6b-linux.launch.json");
const SERVER_RUNNER = join(PROJECT_ROOT, "tools/mcp/server-runner.mjs");

function textFromResult(result) {
  return (result?.content ?? [])
    .filter((item) => item?.type === "text")
    .map((item) => item.text)
    .join("\n")
    .trim();
}

async function callTool(client, name, args = {}, timeout = 15000) {
  const result = await client.callTool({ name, arguments: args }, undefined, { timeout });
  if (result.isError) {
    const error = new Error(`Tool call ${name} failed: ${textFromResult(result)}`);
    error.toolResult = result;
    throw error;
  }
  return result;
}

async function runCommand(client, instance, cmd) {
  const res = await callTool(client, "run_command", { instance, text: cmd });
  return textFromResult(res);
}

async function getActorState(client, instance) {
  const res = await callTool(client, "actor_state", { instance });
  if (res.structuredContent) return res.structuredContent;
  return JSON.parse(textFromResult(res));
}

async function probeAcs(client, instance) {
  await runCommand(client, instance, "pukename rz_debug_fb_probe");
  await new Promise((r) => setTimeout(r, 300));
  const fbRes = await callTool(client, "get_acs_var", { instance, scope: "world", index: 50 });
  const zcRes = await callTool(client, "get_acs_var", { instance, scope: "world", index: 51 });
  const zpRes = await callTool(client, "get_acs_var", { instance, scope: "world", index: 52 });
  const alRes = await callTool(client, "get_acs_var", { instance, scope: "world", index: 53 });
  const cyRes = await callTool(client, "get_acs_var", { instance, scope: "world", index: 54 });
  const blRes = await callTool(client, "get_acs_var", { instance, scope: "world", index: 55 });
  const mxRes = await callTool(client, "get_acs_var", { instance, scope: "world", index: 56 });
  const fbCount = fbRes.structuredContent ? fbRes.structuredContent.value : parseInt(textFromResult(fbRes), 10);
  const zbCheck = zcRes.structuredContent ? zcRes.structuredContent.value : parseInt(textFromResult(zcRes), 10);
  const zbPhase = zpRes.structuredContent ? zpRes.structuredContent.value : parseInt(textFromResult(zpRes), 10);
  const sbeAmmoLen = alRes.structuredContent ? alRes.structuredContent.value : parseInt(textFromResult(alRes), 10);
  const sbeCyan = cyRes.structuredContent ? cyRes.structuredContent.value : parseInt(textFromResult(cyRes), 10);
  const sbeBlue = blRes.structuredContent ? blRes.structuredContent.value : parseInt(textFromResult(blRes), 10);
  const sbeMax = mxRes.structuredContent ? mxRes.structuredContent.value : parseInt(textFromResult(mxRes), 10);
  return { fbCount, zbCheck, zbPhase, sbeAmmoLen, sbeCyan, sbeBlue, sbeMax };
}

async function resetPlayer(client, instance) {
  await callTool(client, "load_map", { instance, mapName: "MM2DW1" });
  await new Promise((r) => setTimeout(r, 1000));
}

async function main() {
  const mcpDir = process.env.ZANDRONUM_MCP_DIR;
  if (!mcpDir) throw new Error("set ZANDRONUM_MCP_DIR");
  const engine = process.env.ZANDRONUM_EXE;
  if (!engine) throw new Error("set ZANDRONUM_EXE");
  const profileFile = process.env.ZANDRONUM_LAUNCH_PROFILES || DEFAULT_PROFILE;
  const server = process.env.ZANDRONUM_MCP_SERVER || join(mcpDir, "dist/server.js");
  const bridgePort = process.env.ZANDRONUM_BRIDGE_PORT || "7777";

  const resolved = loadResolvedProfile(PROJECT_ROOT, profileFile, "mm8bdm-v6b-full");
  const sdkRoot = join(mcpDir, "node_modules/@modelcontextprotocol/sdk/dist/esm");
  const [{ Client }, { StdioClientTransport }] = await Promise.all([
    import(pathToFileURL(join(sdkRoot, "client/index.js"))),
    import(pathToFileURL(join(sdkRoot, "client/stdio.js"))),
  ]);

  const transport = new StdioClientTransport({
    command: process.env.ZANDRONUM_NODE || process.execPath,
    args: [SERVER_RUNNER, server],
    cwd: mcpDir,
    env: {
      ...process.env,
      ZANDRONUM_BRIDGE_PORT: bridgePort,
      ZANDRONUM_EXE: engine,
      ZANDRONUM_LAUNCH_PROFILES: profileFile,
    },
    stderr: "pipe",
  });

  const client = new Client({ name: "verify-boss-multiweapon", version: "1.0.0" });
  await client.connect(transport);

  console.log("Connected to MCP server. Launching mm8bdm-v6b-full...");
  const launchResult = await callTool(
    client,
    "launch_instance",
    launchInstanceArgs(1, resolved.profile),
    90000,
  );
  console.log("Launched:", textFromResult(launchResult).split("\n")[0]);

  // Give engine a moment to load
  await new Promise((r) => setTimeout(r, 2000));

  const startupRes = await callTool(client, "get_startup_errors", { instance: 1 });
  console.log("Startup errors check:", textFromResult(startupRes).split("\n")[0]);

  const results = {};

  try {
    // -------------------------------------------------------------
    // Test 1: GBeast (108)
    // -------------------------------------------------------------
    console.log("\n=== Test 1: GBeast (108) ===");
    await resetPlayer(client, 1);
    await runCommand(client, 1, "pukename rz_debug_MorphMe 0 108");
    await new Promise((r) => setTimeout(r, 1000));

    let actor = await getActorState(client, 1);
    console.log("GBeast class:", actor.class, "initial weapon:", actor.weapon);

    let probe = await probeAcs(client, 1);
    console.log("GBeast ACS probe:", probe);

    // Open wheel
    await runCommand(client, 1, "pukename uh_ww_open");
    await new Promise((r) => setTimeout(r, 500));
    // Select weapon index 3 (GBeast_W4)
    await runCommand(client, 1, "pukename uh_ww_select 3");
    await runCommand(client, 1, "pukename uh_ww_close");
    await new Promise((r) => setTimeout(r, 500));

    actor = await getActorState(client, 1);
    console.log("GBeast ready weapon after wheel select index 3:", actor.weapon);
    results.GBeast = {
      fbCount: probe.fbCount,
      selected: actor.weapon,
      ok: probe.fbCount === 6 && actor.weapon === "GBeast_W4",
    };

    // -------------------------------------------------------------
    // Test 2: SinfulBusterExpert (102)
    // -------------------------------------------------------------
    console.log("\n=== Test 2: SinfulBusterExpert (102) ===");
    await resetPlayer(client, 1);
    await runCommand(client, 1, "pukename rz_debug_MorphMe 0 102");
    await new Promise((r) => setTimeout(r, 1000));

    actor = await getActorState(client, 1);
    console.log("SinfulBusterExpert class:", actor.class, "initial weapon:", actor.weapon);

    probe = await probeAcs(client, 1);
    console.log("SinfulBusterExpert ACS probe:", probe);

    // Try opening wheel with only W1 held
    await runCommand(client, 1, "pukename uh_ww_open");
    await new Promise((r) => setTimeout(r, 500));

    // Try selecting unheld weapon index 2 (W3) - should be ignored!
    await runCommand(client, 1, "pukename uh_ww_select 2");
    await runCommand(client, 1, "pukename uh_ww_close");
    await new Promise((r) => setTimeout(r, 500));

    actor = await getActorState(client, 1);
    console.log("SinfulBusterExpert after trying unheld W3 (should remain W1):", actor.weapon);
    const unheldRejected = (actor.weapon === "SinfulBusterExpert_W1");

    // Now give W2 and select it
    await runCommand(client, 1, "give SinfulBusterExpert_W2 1");
    await new Promise((r) => setTimeout(r, 500));

    await runCommand(client, 1, "pukename uh_ww_open");
    await new Promise((r) => setTimeout(r, 500));
    await runCommand(client, 1, "pukename uh_ww_select 1"); // index 1 = W2
    await runCommand(client, 1, "pukename uh_ww_close");
    await new Promise((r) => setTimeout(r, 500));

    actor = await getActorState(client, 1);
    console.log("SinfulBusterExpert after unlocking and selecting W2:", actor.weapon);
    const unlockSelected = (actor.weapon === "SinfulBusterExpert_W2");

    const ammoOk = (probe.sbeAmmoLen === 10 && probe.sbeCyan === 203 && probe.sbeBlue === 206 && probe.sbeMax === 145);
    console.log("SinfulBusterExpert ammo probe: ammoLen =", probe.sbeAmmoLen, "cyan =", probe.sbeCyan, "blue =", probe.sbeBlue, "max =", probe.sbeMax, "ammoOk =", ammoOk);

    results.SinfulBusterExpert = {
      fbCount: probe.fbCount,
      unheldRejected,
      unlockSelected,
      ammoOk,
      ok: probe.fbCount === 8 && unheldRejected && unlockSelected && ammoOk,
    };

    // -------------------------------------------------------------
    // Test 3: MakeAGoodZero (306)
    // -------------------------------------------------------------
    console.log("\n=== Test 3: MakeAGoodZero (306) ===");
    await resetPlayer(client, 1);
    await runCommand(client, 1, "pukename rz_debug_MorphMe 0 306");
    await new Promise((r) => setTimeout(r, 1000));

    actor = await getActorState(client, 1);
    console.log("MakeAGoodZero class:", actor.class, "initial weapon:", actor.weapon);

    probe = await probeAcs(client, 1);
    console.log("MakeAGoodZero Phase 1 probe:", probe);
    const p1CheckOk = (probe.zbCheck === 1 && probe.zbPhase === 1 && probe.fbCount === -1);

    // Switch to Phase 2: give W2..W7, take W
    await runCommand(client, 1, "give MakeAGoodZero_W2 1");
    await runCommand(client, 1, "give MakeAGoodZero_W3 1");
    await runCommand(client, 1, "give MakeAGoodZero_W4 1");
    await runCommand(client, 1, "give MakeAGoodZero_W5 1");
    await runCommand(client, 1, "give MakeAGoodZero_W6 1");
    await runCommand(client, 1, "give MakeAGoodZero_W7 1");
    await runCommand(client, 1, "take MakeAGoodZero_W 1");
    await runCommand(client, 1, "use MakeAGoodZero_W2");
    await new Promise((r) => setTimeout(r, 500));

    probe = await probeAcs(client, 1);
    console.log("MakeAGoodZero Phase 2 probe:", probe);
    const p2CheckOk = (probe.zbCheck === 1 && probe.zbPhase === 2);

    // Open wheel in Phase 2
    await runCommand(client, 1, "pukename uh_ww_open");
    await new Promise((r) => setTimeout(r, 500));
    // Select index 2 = W4
    await runCommand(client, 1, "pukename uh_ww_select 2");
    await runCommand(client, 1, "pukename uh_ww_close");
    await new Promise((r) => setTimeout(r, 500));

    actor = await getActorState(client, 1);
    console.log("MakeAGoodZero after wheel select in Phase 2:", actor.weapon);

    results.MakeAGoodZero = {
      p1CheckOk,
      p2CheckOk,
      selected: actor.weapon,
      ok: p1CheckOk && p2CheckOk && actor.weapon === "MakeAGoodZero_W4",
    };

    // -------------------------------------------------------------
    // Test 4: Batch A remaining Bosses
    // -------------------------------------------------------------
    console.log("\n=== Test 4: Batch A remaining Bosses ===");
    const batchABosses = [
      { id: 5, name: "KakusaretaSutoka", expectedCount: 3, selectIdx: 1, expectedWep: "KakusaretaSutoka_W2" },
      { id: 18, name: "ArchArcanist", expectedCount: 3, selectIdx: 1, expectedWep: "ArchArcanist_W2" },
      { id: 54, name: "VoidWalker", expectedCount: 4, selectIdx: 2, expectedWep: "VoidWalker_W3" },
      { id: 109, name: "FBeast", expectedCount: 6, selectIdx: 4, expectedWep: "FBeast_W5" },
      { id: 402, name: "FinalSampi", expectedCount: 7, selectIdx: 3, expectedWep: "FinalSampi_W4" },
    ];

    for (const b of batchABosses) {
      await resetPlayer(client, 1);
      await runCommand(client, 1, `pukename rz_debug_MorphMe 0 ${b.id}`);
      await new Promise((r) => setTimeout(r, 1000));

      const p = await probeAcs(client, 1);
      await runCommand(client, 1, "pukename uh_ww_open");
      await new Promise((r) => setTimeout(r, 300));
      await runCommand(client, 1, `pukename uh_ww_select ${b.selectIdx}`);
      await runCommand(client, 1, "pukename uh_ww_close");
      await new Promise((r) => setTimeout(r, 500));

      const act = await getActorState(client, 1);
      console.log(`${b.name}: fb_count=${p.fbCount}, selected=${act.weapon}`);
      results[b.name] = {
        fbCount: p.fbCount,
        selected: act.weapon,
        ok: p.fbCount === b.expectedCount && act.weapon === b.expectedWep,
      };
    }

  } finally {
    console.log("\nCleaning up instance...");
    await callTool(client, "kill_instance", { instance: 1 });
    await client.close();
  }

  console.log("\n=== Final Test Results ===");
  console.log(JSON.stringify(results, null, 2));

  let allPassed = true;
  for (const [k, v] of Object.entries(results)) {
    if (!v.ok) {
      allPassed = false;
      console.error(`FAIL: ${k}`);
    } else {
      console.log(`PASS: ${k}`);
    }
  }

  if (!allPassed) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("Test error:", err);
  process.exit(1);
});
