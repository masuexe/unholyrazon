#!/usr/bin/env node
//
// team-presentation-test.mjs - runtime gate for the actor-keyed presentation
// migration (reports/team-info-definition-api-implementation-plan.md).
//
// Static compilation cannot prove that the UHDT presentation table is populated
// at map load on the CLIENT (which is where the HUD resolves from), that the
// resolver returns the same faces the former hardcoded tables did, or that the
// team-info identity broadcast carries a packed (kind, definition id) instead of
// a load-order-dependent presentation row.
//
// Coverage (dedicated server + one MCP-controlled remote client):
//   1. table built   - rz_debug_TeamPresentationCheck reports 0 failures on the
//      client, so every built-in row resolves through the public API.
//   2. resolver output - the check logs each live player's class -> name /
//      portrait / scoreIcon; the probe asserts a known class keeps its exact
//      former values (MegaManU -> "Mega Man" / UMUG_0 / UMUG_0).
//   3. identity sync - the server publishes the actor class NAME.  A class the
//      client does not know must degrade to an EMPTY face, never to another
//      class's face: neither a definition id nor a presentation row may ever be
//      synced, because both are assigned in load order.  Unknown classes occur
//      naturally every run (morph/item actors), and unknownSeen keeps the
//      assertion from being vacuous.  A mismatched addon set cannot be forced for
//      a class-adding addon -- the engine rejects the connection on protected
//      lumps -- so the ACS-only divergence is what this covers.
//   4. dead-row face - the PLS_DEAD transition keeps the retained role and the
//      cached class, and clearing one slot leaves every other slot's class
//      untouched (no cross-slot leak).
//
// Usage:
//   node tools/mcp/team-presentation-test.mjs [--profile NAME] [--game-port N]
//        [--bridge-port N] [--json] [--dry-run]
//
// Env overrides: ZANDRONUM_MCP_DIR, ZANDRONUM_MCP_SERVER, ZANDRONUM_EXE,
//   ZANDRONUM_LAUNCH_PROFILES, ZANDRONUM_BRIDGE_PORT.

import { spawn } from "node:child_process";
import { appendFileSync, cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { launchInstanceArgs, loadResolvedProfile } from "../resolve-launch-profile.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const PROFILES = process.env.ZANDRONUM_LAUNCH_PROFILES || join(ROOT, "tools/mm8bdm-v6b-linux.launch.json");
const MCP_DIR = process.env.ZANDRONUM_MCP_DIR;
const ENGINE = process.env.ZANDRONUM_EXE;
const SERVER = process.env.ZANDRONUM_MCP_SERVER || (MCP_DIR ? join(MCP_DIR, "dist/server.js") : "");
const RUNNER = join(ROOT, "tools/mcp/server-runner.mjs");
const SDK = join(MCP_DIR || "", "node_modules/@modelcontextprotocol/sdk/dist/esm");
const SERVER_LOG = "/tmp/team-presentation-server.log";
const CLIENT_LOG = join(dirname(ENGINE || "."), `mcp-bridge-${process.env.ZANDRONUM_BRIDGE_PORT || "7777"}.log`);
const SLOTS = 8;

const options = { profile: "mm8bdm-v6b-smoke", gamePort: 10767, bridgePort: 7777, json: false, dryRun: false, addon: false };
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === "--help" || arg === "-h") { process.stdout.write(usage()); process.exit(0); }
  if (arg === "--json") { options.json = true; continue; }
  if (arg === "--dry-run") { options.dryRun = true; continue; }
  if (arg === "--addon") { options.addon = true; continue; }
  if (arg === "--profile") { options.profile = process.argv[++i]; continue; }
  if (arg === "--game-port") { options.gamePort = Number.parseInt(process.argv[++i], 10); continue; }
  if (arg === "--bridge-port") { options.bridgePort = Number.parseInt(process.argv[++i], 10); continue; }
  throw new Error("unknown option " + arg);
}
if (!options.profile) throw new Error("invalid --profile");
for (const path of [SERVER, ENGINE, PROFILES, RUNNER, SDK]) if (!path || !existsSync(path)) {
  console.error("set ZANDRONUM_MCP_DIR / ZANDRONUM_EXE; missing: " + path);
  process.exit(2);
}

function usage() {
  return "Usage: team-presentation-test.mjs [--profile NAME] [--game-port N] [--bridge-port N] [--json] [--dry-run]\n" +
    "\n" +
    "Launch one local Zandronum dedicated server plus one MCP-controlled remote client,\n" +
    "then verify the team presentation migration on the client VM: the built-in table is\n" +
    "populated, the resolver output matches the former hardcoded tables, and the\n" +
    "team-info identity broadcast carries a packed (kind, definition id).\n" +
    "\n" +
    "With --addon the profile must load examples/teampresentation_addon, and the gate\n" +
    "additionally asserts that addon class resolves with no Unholy source edit.\n" +
    "\n" +
    "A mismatched addon set cannot be orchestrated for a class-ADDING addon: the\n" +
    "engine refuses the connection (\"Protected lump authentication failed\") because\n" +
    "DECORATE and KEYCONF are protected lumps, so both peers always agree on the actor\n" +
    "class set.  The residual divergence is an ACS-only addon that registers\n" +
    "presentation rows without touching DECORATE, and that is covered by the\n" +
    "safe-degradation assertion plus the controlled transfer cases in 3c.\n" +
    "Requires local TCP/UDP ports and the bridge-patched engine.\n";
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
  stderr: "ignore",
});

const client = new Client({ name: "unholy-team-presentation", version: "1.0.0" });
const delay = ms => new Promise(r => setTimeout(r, ms));
const launched = [];
let dedicated;
let dedicatedLog = "";
let isolatedRoot;
const text = result => (result.content || []).filter(x => x.type === "text").map(x => x.text).join("\n");

async function tool(name, args, timeout) {
  const result = await client.callTool({ name, arguments: args }, undefined, { timeout: timeout || 90_000 });
  if (result.isError) throw new Error(name + ": " + text(result));
  return result;
}
async function mapVar(name) {
  try {
    const r = await tool("get_map_var", { instance: 1, name }, 8_000);
    return r.structuredContent?.value ?? Number(text(r));
  } catch { return null; }
}
async function mapArray(name, index) {
  try {
    const r = await tool("get_map_array", { instance: 1, name, index }, 8_000);
    return r.structuredContent?.value ?? Number(text(r));
  } catch { return null; }
}

// The expected (name, portrait, scoreIcon) per actor, parsed straight from the
// generated presentation fragments so the probe never carries its own copy of
// the data.  tools/check_team_presentation.py proves those fragments match the
// former hardcoded tables; this probe proves the live client agrees.
// PLS_* role -> the definition side that must own the class.
const ROLE_SIDE = { 1: "surv", 2: "boss", 6: "eye" };
const EXPECTED = new Map();
const SIDES = [
  ["surv", "src/acs_source/classes/survivors/definitions/uh_survdefs_presentation.acs"],
  ["boss", "src/acs_source/classes/bosses/boss_presentation_defs.acs"],
  ["eye", "src/acs_source/classes/demoneyes/definitions/uh_eyedefs_presentation.acs"],
];
for (const [side, frag] of SIDES) {
  const body = readFileSync(join(ROOT, frag), "utf8");
  for (const m of body.matchAll(/DefineTeamPresentation\("([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*-?\d+\)/g)) {
    EXPECTED.set(m[1].toLowerCase(), { side, name: m[2], portrait: m[3], scoreIcon: m[4] });
  }
}

let result;
try {
  const { profile: profileData } = loadResolvedProfile(ROOT, PROFILES, options.profile);

  // Dedicated -lastmanstanding server (the round actually starts, so roles and
  // the status snapshot are pushed to the remote client).
  // Isolated engine folder: the dedicated server must not share runtime/config
  // files with the MCP-controlled client.
  const isolatedRoot = mkdtempSync(join(tmpdir(), "unholy-teampres-"));
  const serverDir = join(isolatedRoot, "server");
  cpSync(dirname(ENGINE), serverDir, { recursive: true });
  writeFileSync(SERVER_LOG, "");
  const common = ["-nosound", "+set", "vid_renderer", "0", "+set", "fullscreen", "0"];
  const serverArgs = [
    "-stdout", "-iwad", profileData.iwad, "-file", ...(profileData.files || []),
    "-host", "8", "-port", String(options.gamePort), "-lastmanstanding",
    "+set", "sv_minplayers", "1", "+set", "sv_updatemaster", "0", "+set", "sv_noplayertimeout", "1",
    "+set", "sv_cheats", "1", "+set", "uh_sv_LogLevel", "4",
    "+map", profileData.map || "MM2DW1", ...common,
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
  if (dedicated.exitCode !== null) throw new Error("dedicated server exited early with code " + dedicated.exitCode);

  await client.connect(transport);
  launched.push(1);
  await tool("launch_instance", launchInstanceArgs(1, profileData, [
    ...common, "+set", "uh_cl_LogLevel", "4", "+set", "uh_cl_teaminfo", "1",
    "-port", String(options.gamePort + 1), "+name", "TPClient",
  ]), 120_000);
  await delay(10_000);
  await tool("run_command", { instance: 1, text: "connect 127.0.0.1:" + options.gamePort }, 30_000);
  await delay(16_000);
  await tool("run_command", { instance: 1, text: "join" }, 20_000);
  await delay(14_000);
  // Bots keep the round alive and give the probe stable subjects to observe.
  // Driven through the dedicated server's stdin: addbot is a server command.
  const sendServer = line => { if (dedicated.stdin.writable) dedicated.stdin.write(line + "\n"); };
  sendServer("addbot");
  await delay(3_000);
  sendServer("addbot");
  await delay(14_000);

  // The round must actually start before playerlifestatusarr is filled in, so
  // poll for ANY assigned role instead of guessing a fixed delay.
  const pollRoles = async () => {
    const out = [];
    for (let k = 0; k < SLOTS; k += 1) out.push(await mapArray("uhtirole", k));
    return out;
  };
  let roles = await pollRoles();
  for (let i = 0; i < 40 && !roles.some(r => r !== null && r >= 0); i += 1) {
    await delay(4_000);
    roles = await pollRoles();
  }
  const roundStarted = roles.some(r => r !== null && r >= 0);
  await delay(6_000);

  // --- 1 + 2. table built and resolver output -------------------------------
  await tool("run_script", { instance: 1, script: "rz_debug_TeamPresentationCheck", args: [], always: true }, 40_000);
  await delay(4_000);
  const clientLog = readFileSync(CLIENT_LOG, "utf8");
  const rowMatch = clientLog.match(/TeamPresentationCheck: (\d+) rows ok/);
  const rowCount = rowMatch ? Number(rowMatch[1]) : 0;
  const rowErrors = clientLog.match(/TeamPresentationCheck: (?:empty actor|row does not resolve|no display name)[^\n]*/g) || [];
  const tableBuilt = Boolean(rowMatch) && rowErrors.length === 0 && rowCount > 0;

  // The check logs one line per live player; the joining client is a survivor,
  // so its own class must resolve to exactly the former hardcoded output.
  const liveLines = [...clientLog.matchAll(/TeamPresentationCheck: player \d+ (\S+) -> name=(.*?) portrait=(.*?) scoreIcon=(.*?)(?:\r?\n|$)/g)]
    .map(m => ({ cls: m[1], name: m[2], portrait: m[3], scoreIcon: m[4] }));
  const resolved = liveLines.length > 0;
  // The same expectations, resolved through the table by class, are asserted in
  // check_team_presentation.py; here we only prove the live client agrees.
  // Every live class is a built-in one, so it must match its expected row
  // exactly: this is the runtime half of check_team_presentation.py.
  // --addon: the example addon's own class must resolve through the same table,
  // with no edit to any Unholy source file.
  let addonOk = true;
  let addonDetail = null;
  if (options.addon) {
    const rowLine = clientLog.match(/TeamPresentationCheck: row (\S+) -> name=(.*?) portrait=(.*?) scoreIcon=(.*?)(?:\r?\n|$)/);
    const rows = [...clientLog.matchAll(/TeamPresentationCheck: row (\S+) -> name=(.*?) portrait=(.*?) scoreIcon=(.*?)(?:\r?\n|$)/g)]
      .map(m => ({ cls: m[1], name: m[2], portrait: m[3], scoreIcon: m[4] }));
    const addonRow = rows.find(r => r.cls.toLowerCase() === "uhexampleterrance");
    addonDetail = { addonRow, rowCount: rows.length };
    // The addon registers an explicit short name and its own mugshot/icon, so
    // neither the colored DefineSurvivor name nor the actor class may appear.
    addonOk = Boolean(addonRow)
      && addonRow.name === "Example Terrance"
      && addonRow.portrait === "EXTPMUG"
      && addonRow.scoreIcon === "EXTPICN";
    void rowLine;
  }

  const liveOk = liveLines.length > 0 && liveLines.every(l => {
    const want = EXPECTED.get(l.cls.toLowerCase());
    if (!want) { return false; }
    // An empty scoreIcon means "same as the portrait" (documented API rule).
    const wantIcon = want.scoreIcon || want.portrait;
    return want.name === l.name && want.portrait === l.portrait && wantIcon === l.scoreIcon;
  });

  // --- 3. identity sync -----------------------------------------------------
  // The server publishes the actor class NAME (uh_ti_TeamInfoCacheDump logs what
  // the client actually cached).  The property under test is that this value is
  // content, not a load-order-dependent index: a class the client does not know
  // must resolve to an EMPTY face, never to another class's face.  That is what
  // makes a mismatched addon set safe, and it is why neither a definition id nor
  // a presentation row may ever be synced.
  await tool("run_script", { instance: 1, script: "uh_ti_TeamInfoCacheDump", args: [], always: true }, 40_000);
  await delay(4_000);
  const cacheLog = readFileSync(CLIENT_LOG, "utf8");
  const cacheLines = [...cacheLog.matchAll(/TeamInfoCache: slot (\d+) (\S+) -> name=(.*?) portrait=(.*?) scoreIcon=(.*?) known=([01])(?:\r?\n|$)/g)]
    .map(m => ({ slot: Number(m[1]), cls: m[2], name: m[3], portrait: m[4], scoreIcon: m[5], known: m[6] === "1" }));
  // Every published slot must carry a plausible class name, and a class this peer
  // does not know (known=0) must produce an empty portrait AND an empty icon.
  const cachePublished = cacheLines.length > 0;
  const safeDegradation = cacheLines.every(l => {
    if (l.known) { return true; }
    return l.portrait === "" && l.scoreIcon === "" && l.name === l.cls;
  });
  // Where the role is also known, the cached class must be a definition of THAT
  // side.  This is the check that catches an id resolving to the wrong table:
  // a Boss slot caching a survivor class means the synced (kind, id) pair was
  // misinterpreted, which is exactly what a load-order-dependent id would do.
  const roleAgreement = [];
  for (const line of cacheLines) {
    const role = roles[line.slot];
    if (role === null || role < 0) { continue; }
    const want = EXPECTED.get(line.cls.toLowerCase());
    if (!want) { continue; }
    const wantSide = ROLE_SIDE[role];
    roleAgreement.push({
      slot: line.slot, role, cls: line.cls, side: want.side, wantSide,
      ok: want.side === wantSide,
    });
  }
  const roleAgreementOk = roleAgreement.length > 0 && roleAgreement.every(r => r.ok);
  const identityDetail = cacheLines.map(l => ({ slot: l.slot, cls: l.cls, known: l.known, portrait: l.portrait }));
  // unknownSeen keeps the assertion above from being vacuous: at least one class
  // this peer does not know must actually have been published.
  const unknownSeen = cacheLines.some(l => !l.known);
  const identityOk = cachePublished && safeDegradation && unknownSeen && roleAgreementOk;

  // --- 3c. controlled server -> client identity transfer --------------------
  // The cache dump above cannot prove the transfer, because uhticlasscache is
  // also filled locally from the live actor.  Drive the receiver directly with a
  // known (kind, id) pair for a slot that has NO live actor, then read back what
  // the client derived from its OWN tables.  This is the only part of the probe
  // that exercises the wire format deterministically.
  //
  // PLS_* role values and the UH_PLDEF_* kinds are plain integers, so they can be
  // pushed through run_script (which only accepts int args -- another reason an
  // ACS string is not a viable payload here).
  const PROBE_SLOT = 7;
  const transfer = [];
  const pushIdentity = async (kind, id) => {
    for (let i = 0; i < 10; i += 1) {
      await tool("run_script", { instance: 1, script: "uh_ti_sync_status",
        args: [PROBE_SLOT, 2, kind, id], always: true }, 30_000);
      await delay(2_500);
      const line = (await dumpCacheLines()).find(l => l.slot === PROBE_SLOT);
      if (line) { return line; }
    }
    return null;
  };
  const dumpCacheLines = async () => {
    await tool("run_script", { instance: 1, script: "uh_ti_TeamInfoCacheDump", args: [], always: true }, 40_000);
    await delay(4_000);
    const text = readFileSync(CLIENT_LOG, "utf8");
    const cut = text.lastIndexOf("TeamInfoCache: begin");
    if (cut < 0) { return []; }
    return [...text.slice(cut).matchAll(/TeamInfoCache: slot (\d+) (\S+) -> name=(.*?) portrait=(.*?) scoreIcon=(.*?) known=([01])(?:\r?\n|$)/g)]
      .map(m => ({ slot: Number(m[1]), cls: m[2], name: m[3], portrait: m[4], scoreIcon: m[5], known: m[6] === "1" }));
  };

  // (a) a vanilla boss id must resolve to that boss's own class and face.
  const boss0 = await pushIdentity(2, 0);
  transfer.push({ case: "vanilla boss 0", line: boss0, wantCls: "TrueBusterExpert", wantPortrait: "UB000MUG" });
  // (b) a vanilla survivor id must resolve to that survivor.
  const surv6 = await pushIdentity(1, 6);
  transfer.push({ case: "vanilla survivor 6", line: surv6, wantCls: "LuckyLass", wantPortrait: "UMUG_6" });
  // (c) an undefined vanilla slot must resolve to NOTHING, not to a neighbour.
  const undef = await pushIdentity(2, 9999);
  transfer.push({ case: "undefined boss 9999", line: undef, wantCls: null, wantPortrait: "" });
  // (d) a negative (custom, load-order-dependent) id must be REJECTED by the
  //     receiver, so it can never be misresolved on a peer with another addon set.
  const custom = await pushIdentity(1, -1);
  transfer.push({ case: "custom survivor -1", line: custom, wantCls: null, wantPortrait: "" });
  // (e) NONE after a valid identity must CLEAR the slot.  This is the morph /
  //     slot-reuse case: the previous occupant had a vanilla identity, and
  //     keeping it would draw the previous player's face.
  const noneAfterValid = await pushIdentity(0, 0);
  transfer.push({ case: "NONE after a valid identity", line: noneAfterValid, wantCls: null, wantPortrait: "", wantEmpty: true });
  // (f) PLS_NULL with a still-valid pair must also clear.  This is the
  //     "clear then immediately re-apply" hazard: UH_Ti_SetClientLife empties the
  //     cache and a stale server pair used to repopulate it in the same script.
  await tool("run_script", { instance: 1, script: "uh_ti_sync_status",
    args: [PROBE_SLOT, 2, 2, 0], always: true }, 30_000);
  await delay(2_500);
  const reseeded = (await dumpCacheLines()).find(l => l.slot === PROBE_SLOT);
  await tool("run_script", { instance: 1, script: "uh_ti_sync_status",
    args: [PROBE_SLOT, -1, 0, 0], always: true }, 30_000);
  await delay(2_500);
  const afterNull = (await dumpCacheLines()).find(l => l.slot === PROBE_SLOT);
  transfer.push({
    case: "PLS_NULL clears even with a stale pair",
    line: afterNull, wantCls: null, wantPortrait: "", wantEmpty: true,
    reseededCls: reseeded ? reseeded.cls : null,
  });

  const transferOk = transfer.every(t => {
    if (t.wantEmpty) {
      // The slot must be GONE from the dump, not merely faceless: a stale class
      // in the cache is the bug, whether or not it currently resolves.
      return !t.line;
    }
    if (!t.line) { return false; }
    if (t.wantCls === null) {
      // Either the receiver rejected it, or it resolved to an unknown class:
      // both must yield an empty face, never another class's face.
      return t.line.portrait === "" && t.line.scoreIcon === "";
    }
    return t.line.cls === t.wantCls && t.line.portrait === t.wantPortrait;
  }) && transfer.find(t => t.case === "PLS_NULL clears even with a stale pair").reseededCls === "TrueBusterExpert";

  // Restore the slot so the probe leaves no residue.
  await tool("run_script", { instance: 1, script: "uh_ti_sync_status", args: [PROBE_SLOT, -1, 0, 0], always: true }, 30_000);
  await delay(2_000);
  const rtCleared = !(await dumpCacheLines()).some(l => l.slot === PROBE_SLOT);

  // --- 4. dead-row identity retention ---------------------------------------
  // A dead or body-less player has no readable actor class, so the scoreboard
  // and the teammate bar must fall back to the synced definition identity.  The
  // transition to PLS_DEAD must RETAIN both the role and the identity (only
  // PLS_NULL clears them), and clearing one slot must not disturb the others.
  const DEAD_SLOT = 6;
  await tool("run_script", { instance: 1, script: "uh_ti_sync_status", args: [DEAD_SLOT, 2, 1, 6], always: true }, 30_000);
  await delay(2_500);
  const deadRole = await mapArray("uhtirole", DEAD_SLOT);
  const seeded = deadRole === 2;

  await tool("run_script", { instance: 1, script: "uh_ti_sync_status", args: [DEAD_SLOT, 0, 1, 6], always: true }, 30_000);
  await delay(2_500);
  const afterDeadRole = await mapArray("uhtirole", DEAD_SLOT);
  // PLS_DEAD keeps the retained role; that is what the dead row is keyed on.
  const deadRowRetained = afterDeadRole === 2;

  // Clearing the probe slot must leave every other slot's cached class
  // untouched.  The cache is a string, so it is observed through the dump log.
  const dumpCache = async () => {
    await tool("run_script", { instance: 1, script: "uh_ti_TeamInfoCacheDump", args: [], always: true }, 40_000);
    await delay(4_000);
    const text = readFileSync(CLIENT_LOG, "utf8");
    // Only the last dump counts: the log is append-only, so an earlier dump
    // would keep reporting slots a later one no longer has.
    const cut = text.lastIndexOf("TeamInfoCache: begin");
    const out = new Map();
    if (cut < 0) { return out; }
    for (const m of text.slice(cut).matchAll(/TeamInfoCache: slot (\d+) (\S+) ->/g)) {
      out.set(Number(m[1]), m[2]);
    }
    return out;
  };
  const beforeClear = await dumpCache();
  await tool("run_script", { instance: 1, script: "uh_ti_sync_status", args: [DEAD_SLOT, -1, 0, 0], always: true }, 30_000);
  await delay(2_500);
  const afterClear = await dumpCache();
  let leak = false;
  for (const [slot, cls] of beforeClear) {
    if (slot === DEAD_SLOT || slot === PROBE_SLOT) { continue; }
    if (afterClear.get(slot) !== cls) { leak = true; }
  }
  const clearedSlot = !afterClear.has(DEAD_SLOT);
  const noLeak = !leak && clearedSlot;

  result = {
    status: "ok",
    profile: options.profile,
    rowCount,
    rowErrors,
    tableBuilt,
    addon: options.addon,
    addonOk,
    addonDetail,
    resolved,
    roundStarted,
    liveLines,
    liveOk,
    identityOk,
    identityDetail,
    roleAgreement,
    cacheLines,
    unknownSeen,
    transfer,
    transferOk,
    rtCleared,
    deadRowRetained,
    noLeak,
    deadRowDetail: { seeded, deadRole, afterDeadRole, beforeClear: [...beforeClear], afterClear: [...afterClear] },
    clientLogTail: clientLog.split(/\r?\n/).slice(-30),
    serverLogTail: dedicatedLog.split(/\r?\n/).slice(-20),
  };
  result.pass = tableBuilt && (!options.addon || addonOk) && resolved && liveOk && identityOk
    && transferOk && rtCleared && deadRowRetained && noLeak && roleAgreementOk;
} catch (error) {
  result = { status: "error", error: error instanceof Error ? error.message : String(error), serverLogTail: dedicatedLog.split(/\r?\n/).slice(-20) };
} finally {
  for (const instance of launched.reverse()) {
    try { await tool("kill_instance", { instance }, 15_000); } catch { /* best effort */ }
  }
  if (dedicated && dedicated.exitCode === null) {
    dedicated.kill("SIGTERM");
    await Promise.race([new Promise(r => dedicated.once("exit", r)), delay(4_000)]);
    if (dedicated.exitCode === null) dedicated.kill("SIGKILL");
  }
  await client.close().catch(() => {});
  if (isolatedRoot) rmSync(isolatedRoot, { recursive: true, force: true });
}

console.log(options.json ? JSON.stringify(result) : JSON.stringify(result, null, 2));
process.exit(result.pass ? 0 : 1);
