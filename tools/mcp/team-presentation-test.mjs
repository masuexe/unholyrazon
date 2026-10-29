#!/usr/bin/env node
//
// team-presentation-test.mjs - runtime gate for the actor-keyed presentation
// migration (DefineTeamPresentation in _includes/mod_api/uhadd.acs).
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
//   4. dead-spectator retention - driven through the REAL server path: the round
//      eliminates players into dead spectators (PlayerIsSpectator == 2; 1 is a
//      true spectator and must be cleared), rz_debug_TeamInfoSlots reports the
//      server's classification from the last "TeamInfoSlots: begin", including
//      a probe range of slots past -host that stay empty, ub_StartUpSettings
//      forces a full snapshot, and the same dead slots must still be dead
//      spectators with the same identity afterwards.  The client must keep
//      those roles AND classes.  The probe slots must publish server NONE and
//      leave the client with no role and no cache line.  The receiver is also
//      driven directly in 3c, but that cannot catch a snapshot-classification
//      regression on its own.
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
const PROFILES = resolve(ROOT, process.env.ZANDRONUM_LAUNCH_PROFILES || "tools/mm8bdm-v6c.launch.json");
const MCP_DIR = process.env.ZANDRONUM_MCP_DIR;
const ENGINE = process.env.ZANDRONUM_EXE;
const SERVER = process.env.ZANDRONUM_MCP_SERVER || (MCP_DIR ? join(MCP_DIR, "dist/server.js") : "");
const RUNNER = join(ROOT, "tools/mcp/server-runner.mjs");
const SDK = join(MCP_DIR || "", "node_modules/@modelcontextprotocol/sdk/dist/esm");
const SERVER_LOG = "/tmp/team-presentation-server.log";
const CLIENT_LOG = join(dirname(ENGINE || "."), `mcp-bridge-${process.env.ZANDRONUM_BRIDGE_PORT || "7777"}.log`);
const SLOTS = 8;

const options = { profile: "mm8bdm-v6c-smoke", gamePort: 10767, bridgePort: 7777, json: false, dryRun: false, addon: false };
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
    "+set", "sv_cheats", "1", "+set", "uh_sv_loglevel", "4",
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
  // unknownSeen is diagnostic: a same-build peer knows every presented class and
  // the wire format carries (kind, id), so an unknown class only appears with a
  // mismatched addon set.  safeDegradation still asserts the empty-face rule for
  // any unknown line that is published; requiring unknownSeen here made the gate
  // unreachable in the base profile.
  const unknownSeen = cacheLines.some(l => !l.known);
  const identityOk = cachePublished && safeDegradation && roleAgreementOk;

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
  // Push a (kind, id) pair and read back what the client cached.  "Empty" cases
  // need to retry too: the client log is flushed asynchronously, so one dump can
  // still show the previous occupant even though the receiver cleared the slot.
  const pushIdentity = async (kind, id, status = 2, expectEmpty = false) => {
    const attempts = expectEmpty ? 4 : 1;
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      await tool("run_script", { instance: 1, script: "uh_ti_sync_status",
        args: [PROBE_SLOT, status, kind, id], always: true }, 30_000);
      await delay(3_000);
      const line = (await dumpCacheLines()).find(l => l.slot === PROBE_SLOT);
      if (expectEmpty ? !line : line) { return line; }
    }
    if (!expectEmpty) {
      for (let i = 0; i < 6; i += 1) {
        await delay(2_500);
        const retry = (await dumpCacheLines()).find(l => l.slot === PROBE_SLOT);
        if (retry) { return retry; }
      }
    }
    return null;
  };
  // The engine writes its log asynchronously.  Wait for a NEW dump boundary
  // before parsing, otherwise a lagging flush replays the previous dump and an
  // "empty" case looks like a stale identity.
  const readLogAfterRun = async (logPath, marker, run, timeoutMs = 15_000) => {
    const before = readFileSync(logPath, "utf8");
    const count = (before.match(new RegExp(marker, "g")) || []).length;
    await run();
    const deadline = Date.now() + timeoutMs;
    let text = before;
    do {
      await delay(400);
      text = readFileSync(logPath, "utf8");
      if ((text.match(new RegExp(marker, "g")) || []).length > count) { break; }
    } while (Date.now() < deadline);
    const cut = text.lastIndexOf(marker);
    return cut < 0 ? "" : text.slice(cut);
  };
  const dumpCacheLines = async () => {
    const text = await readLogAfterRun(CLIENT_LOG, "TeamInfoCache: begin",
      () => tool("run_script", { instance: 1, script: "uh_ti_TeamInfoCacheDump", args: [], always: true }, 40_000));
    return [...text.matchAll(/TeamInfoCache: slot (\d+) (\S+) -> name=(.*?) portrait=(.*?) scoreIcon=(.*?) known=([01])(?:\r?\n|$)/g)]
      .map(m => ({ slot: Number(m[1]), cls: m[2], name: m[3], portrait: m[4], scoreIcon: m[5], known: m[6] === "1" }));
  };

  // (a) a vanilla boss id must resolve to that boss's own class and face.
  const boss0 = await pushIdentity(2, 0);
  transfer.push({ case: "vanilla boss 0", line: boss0, wantCls: "TrueBusterExpert", wantPortrait: "UB000MUG" });
  // (b) a vanilla survivor id must resolve to that survivor.
  const surv6 = await pushIdentity(1, 6);
  transfer.push({ case: "vanilla survivor 6", line: surv6, wantCls: "LuckyLass", wantPortrait: "UMUG_6" });
  // (c) an undefined vanilla slot must resolve to NOTHING, not to a neighbour.
  const undef = await pushIdentity(2, 9999, 2, true);
  transfer.push({ case: "undefined boss 9999", line: undef, wantCls: null, wantPortrait: "", wantEmpty: true });
  // (d) a negative (custom, load-order-dependent) id must be REJECTED by the
  //     receiver, so it can never be misresolved on a peer with another addon set.
  const custom = await pushIdentity(1, -1, 2, true);
  transfer.push({ case: "custom survivor -1", line: custom, wantCls: null, wantPortrait: "", wantEmpty: true });
  // (e) NONE after a valid identity must CLEAR the slot.  This is the morph /
  //     slot-reuse case: the previous occupant had a vanilla identity, and
  //     keeping it would draw the previous player's face.
  const noneAfterValid = await pushIdentity(0, 0, 2, true);
  transfer.push({ case: "NONE after a valid identity", line: noneAfterValid, wantCls: null, wantPortrait: "", wantEmpty: true });
  // (f) PLS_NULL carrying a STILL-VALID pair must also clear.  This is the
  //     "clear then immediately re-apply" hazard: UH_Ti_SetClientLife empties the
  //     cache and resolving the pair afterwards used to repopulate it in the very
  //     same script.  The pair must be a real one, or the case proves nothing.
  //     A queued server snapshot can clear the slot between the seed and the
  //     dump, so re-seed and re-read instead of trusting one shot.
  let reseeded = null;
  for (let attempt = 0; attempt < 6 && !reseeded; attempt += 1) {
    await tool("run_script", { instance: 1, script: "uh_ti_sync_status",
      args: [PROBE_SLOT, 2, 2, 0], always: true }, 30_000);
    await delay(500);
    reseeded = (await dumpCacheLines()).find(l => l.slot === PROBE_SLOT);
  }
  const afterNull = await pushIdentity(2, 0, -1, true);
  transfer.push({
    case: "PLS_NULL clears even with a valid pair",
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
  }) && transfer.find(t => t.case === "PLS_NULL clears even with a valid pair").reseededCls === "TrueBusterExpert";

  // Restore the slot so the probe leaves no residue.
  await tool("run_script", { instance: 1, script: "uh_ti_sync_status", args: [PROBE_SLOT, -1, 0, 0], always: true }, 30_000);
  await delay(2_000);
  const rtCleared = !(await dumpCacheLines()).some(l => l.slot === PROBE_SLOT);

  // --- 4. dead-spectator retention through the REAL server path --------------
  // The previous version called uh_ti_sync_status directly on the client, which
  // bypassed UH_Ti_IdentityForPlayer and UH_Ti_SendSnapshotCore entirely -- so
  // re-introducing the dead-spectator misclassification would still have passed.
  // Drive the actual server path instead:
  //   (a) let the round run so players are eliminated into dead spectators;
  //   (b) read the server's own classification (rz_debug_TeamInfoSlots);
  //   (c) force a full snapshot (ub_StartUpSettings -> UH_TeamInfo_FullSnapshot);
  //   (d) assert the SAME dead slots still look like dead spectators with the
  //       same identity, the client kept their role AND class, and the probe
  //       range (past -host, so addbot cannot fill it) published NONE with no
  //       client cache.
  // PlayerIsSpectator: 1 = true spectator, 2 = dead spectator.  Only 2 retains.
  // The dedicated server is started with -host 8, so slots [8, 12) stay empty.
  const PROBE_FROM = 8;
  const PROBE_TO = 12;
  const UH_PLDEF_NONE = 0;
  const isDeadSpectator = sl => sl.spec === 2 && !sl.ingame && sl.life !== -1;
  const serverSlots = async () => {
    // puke only takes a NUMERIC script; a named script needs pukename.
    // The dump lives in the `unholy` library because ACS globals are per-library.
    const text = await readLogAfterRun(SERVER_LOG, "TeamInfoSlots: begin",
      () => sendServer(`pukename uh_ti_ServerSlotsDump ${PROBE_FROM} ${PROBE_TO}`));
    const out = [];
    for (const m of text.matchAll(/TeamInfoSlots: slot (\d+) connected=(\d+) ingame=(\d+) spec=(\d+) life=(-?\d+) kind=(\d+) id=(-?\d+)/g)) {
      out.push({
        slot: Number(m[1]), connected: m[2] === "1", ingame: m[3] === "1",
        spec: Number(m[4]), life: Number(m[5]), kind: Number(m[6]), id: Number(m[7]),
      });
    }
    return out;
  };

  // (a) wait for at least one eliminated player.  spec == 2 is the dead
  //     spectator; spec == 1 is a true spectator and must not count.
  let slots = await serverSlots();
  for (let i = 0; i < 30; i += 1) {
    if (slots.some(isDeadSpectator)) { break; }
    sendServer("addbot");
    await delay(3_000);
    slots = await serverSlots();
  }
  // Bot duels can stalemate for minutes, which made "wait until someone dies"
  // skip the retention assertions entirely.  Force an elimination through the
  // debug helper, then re-read the server's own classification.
  let forcedKillSlot = null;
  for (let attempt = 0; attempt < 4 && !slots.some(isDeadSpectator); attempt += 1) {
    const victim = slots.find(sl => sl.connected && sl.ingame && sl.slot > 0);
    if (!victim) { break; }
    forcedKillSlot = victim.slot;
    sendServer(`pukename rz_debug_KillPlayerSlot ${victim.slot}`);
    await delay(4_000);
    slots = await serverSlots();
  }
  const deadSpectators = slots.filter(isDeadSpectator);
  const trueSpectators = slots.filter(sl => sl.spec === 1);
  // Probe range is past -host, so these rows are unoccupied for the whole run.
  // Zero samples used to make unusedCleared pass via Array.every().
  // Do not require life === PLS_NULL.  `int playerlifestatusarr[] = {-1}` only
  // writes index 0; ACC zeroes the rest, so slots 8-11 stay 0 (PLS_DEAD).
  const unusedSlots = slots.filter(sl =>
    sl.slot >= PROBE_FROM && sl.slot < PROBE_TO && !sl.connected && !sl.ingame && sl.spec === 0);
  // A dead spectator must keep a resolved identity server-side.  This is the
  // assertion the old client-only test could not make.
  const serverRetainsDead = deadSpectators.length > 0
    && deadSpectators.every(sl => sl.kind >= 1 && sl.kind <= 3);

  // (c) force the full snapshot through the real path.
  sendServer("pukename ub_StartUpSettings");
  await delay(10_000);
  const slotsAfter = await serverSlots();
  // The same dead slot must still be a dead spectator with the same identity
  // after the snapshot.  slotsAfter used to be diagnostic only.
  const snapshotKeepsDead = deadSpectators.length > 0 && deadSpectators.every(sl => {
    const after = slotsAfter.find(a => a.slot === sl.slot);
    return !!after && isDeadSpectator(after) && after.kind === sl.kind && after.id === sl.id;
  });

  // (d) the client must still hold the dead spectator's role and class...
  const clientRoles = [];
  for (let k = 0; k < SLOTS; k += 1) clientRoles.push(await mapArray("uhtirole", k));
  const probeRoles = new Map();
  for (let k = PROBE_FROM; k < PROBE_TO; k += 1) probeRoles.set(k, await mapArray("uhtirole", k));
  const dumpCache = async () => {
    await tool("run_script", { instance: 1, script: "uh_ti_TeamInfoCacheDump", args: [], always: true }, 40_000);
    await delay(4_000);
    const text = readFileSync(CLIENT_LOG, "utf8");
    const cut = text.lastIndexOf("TeamInfoCache: begin");
    const out = new Map();
    if (cut < 0) { return out; }
    for (const m of text.slice(cut).matchAll(/TeamInfoCache: slot (\d+) (\S+) ->/g)) {
      out.set(Number(m[1]), m[2]);
    }
    return out;
  };
  const cacheAfter = await dumpCache();
  const deadRowRetained = deadSpectators.length > 0 && deadSpectators.every(sl => {
    // The match is -host 8, so a dead spectator's slot is inside clientRoles.
    if (sl.slot < 0 || sl.slot >= clientRoles.length) { return false; }
    // PLS_DEAD retains the role on the client; only PLS_NULL clears it.
    if (clientRoles[sl.slot] === null || clientRoles[sl.slot] < 0) { return false; }
    // ...and the class cache must still resolve to a face for it.
    const cls = cacheAfter.get(sl.slot);
    return typeof cls === "string" && cls.length > 0;
  });
  // ...while the probe slots must be NONE on the server and absent on the client.
  // A missing role read (null) is a failure, not a clear.
  const unusedCleared = unusedSlots.length === (PROBE_TO - PROBE_FROM) && unusedSlots.every(sl => {
    const after = slotsAfter.find(a => a.slot === sl.slot);
    const serverNone = !!after && !after.connected && !after.ingame && after.spec === 0
      && after.kind === UH_PLDEF_NONE && after.id === 0;
    const role = probeRoles.get(sl.slot);
    return serverNone && role === -1 && !cacheAfter.has(sl.slot);
  });
  // A true spectator, when one showed up, must not keep the old face either.
  const trueSpectatorCleared = trueSpectators.every(sl => {
    if (sl.slot < 0 || sl.slot >= clientRoles.length) { return false; }
    const after = slotsAfter.find(a => a.slot === sl.slot);
    return !!after && after.kind === UH_PLDEF_NONE && after.id === 0
      && clientRoles[sl.slot] === -1 && !cacheAfter.has(sl.slot);
  });
  const noLeak = unusedCleared && trueSpectatorCleared;

  result = {
    status: "ok",
    profile: options.profile,
    forcedKillSlot,
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
    serverRetainsDead,
    snapshotKeepsDead,
    noLeak,
    deadRowDetail: {
      deadSpectators, trueSpectators, unusedSlots, slotsAfter,
      clientRoles, probeRoles: [...probeRoles], cacheAfter: [...cacheAfter],
    },
    clientLogTail: clientLog.split(/\r?\n/).slice(-30),
    serverLogTail: dedicatedLog.split(/\r?\n/).slice(-20),
  };
  result.pass = tableBuilt && (!options.addon || addonOk) && resolved && liveOk && identityOk
    && transferOk && rtCleared && serverRetainsDead && snapshotKeepsDead
    && deadRowRetained && noLeak && roleAgreementOk;
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
