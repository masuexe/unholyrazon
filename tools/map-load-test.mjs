#!/usr/bin/env node

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadResolvedProfile } from "./resolve-launch-profile.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_PROFILES = join(ROOT, "tools/mm8bdm-v6c.launch.json");

function usage() {
  return `Usage: map-load-test.mjs [options] <map> [<map> ...]

Launch one headless engine per map with a resolved profile, wait for the map
banner and report startup fatals. Proves a genuine map loads with the current
mod; it does not run gameplay.

Options:
  --profile NAME       launch profile (default: mm8bdm-v6c-smoke)
  --profile-file PATH  profile file (default: ZANDRONUM_LAUNCH_PROFILES or
                       tools/mm8bdm-v6c.launch.json)
  --timeout-sec N      per-map banner timeout (default: 60)
  --json               emit one JSON object
  --help               show help

Environment: ZANDRONUM_EXE, ZANDRONUM_LAUNCH_PROFILES
`;
}

const options = { profile: "mm8bdm-v6c-smoke", profileFile: process.env.ZANDRONUM_LAUNCH_PROFILES || DEFAULT_PROFILES, timeoutSec: 60, json: false, maps: [] };
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === "--help" || arg === "-h") { console.log(usage()); process.exit(0); }
  if (arg === "--json") { options.json = true; continue; }
  if (arg === "--profile") { options.profile = process.argv[++i] || ""; continue; }
  if (arg === "--profile-file") { options.profileFile = process.argv[++i] || ""; continue; }
  if (arg === "--timeout-sec") { options.timeoutSec = Number.parseInt(process.argv[++i], 10); continue; }
  if (arg.startsWith("--")) throw new Error(`unknown option ${arg}`);
  options.maps.push(arg);
}
if (!options.profile || !options.maps.length || !Number.isInteger(options.timeoutSec) || options.timeoutSec < 1) {
  console.error(usage());
  process.exit(2);
}
const ENGINE = process.env.ZANDRONUM_EXE;
if (!ENGINE) throw new Error("set ZANDRONUM_EXE to the bridge-patched Zandronum binary");
if (!existsSync(ENGINE)) throw new Error(`engine not found: ${ENGINE}`);
const profileFile = resolve(ROOT, options.profileFile);
if (!existsSync(profileFile)) throw new Error(`profiles not found: ${profileFile}`);
const { profile } = loadResolvedProfile(ROOT, profileFile, options.profile);

function escapeRe(text) { return text.replace(/[.*+?^$\{\}()|[\]\\]/g, "\\$&"); }

function run(map) {
  return new Promise((resolveRun) => {
    const argv = [];
    if (profile.config) argv.push("-config", profile.config);
    if (profile.iwad) argv.push("-iwad", profile.iwad);
    if (profile.files?.length) argv.push("-file", ...profile.files);
    argv.push("-nosound", "+set", "vid_renderer", "0", "+set", "fullscreen", "0", "+set", "sv_cheats", "1", "+map", map);
    argv.push(...(profile.extraArgs || []));
    const child = spawn(ENGINE, argv, {
      cwd: dirname(ENGINE),
      env: { ...process.env, SDL_VIDEODRIVER: process.env.SDL_VIDEODRIVER || "offscreen" },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let out = "";
    let settled = false;
    const started = Date.now();
    const bannerRe = new RegExp("(^|\\n)\\s*" + escapeRe(map) + "\\s*-", "i");
    const fatalRe = /script error|unknown actor|fatal error|invalid data encountered|execution could not continue/i;
    const finish = (why) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (child.exitCode === null) child.kill("SIGTERM");
      const fatal = out.split(/\r?\n/).filter((line) => fatalRe.test(line));
      resolveRun({ map, loaded: bannerRe.test(out), fatal: fatal.slice(0, 10), why, secs: Math.round((Date.now() - started) / 1000) });
    };
    for (const stream of [child.stdout, child.stderr]) stream.on("data", (chunk) => {
      out = (out + chunk).slice(-200000);
      if (bannerRe.test(out)) finish("banner");
    });
    const timer = setTimeout(() => finish("timeout"), options.timeoutSec * 1000);
    child.once("exit", (code) => finish("exit:" + code));
  });
}

const results = [];
for (const map of options.maps) results.push(await run(map));
const failed = results.filter((r) => !r.loaded || r.fatal.length);
if (options.json) {
  console.log(JSON.stringify({ status: failed.length ? "fail" : "pass", profile: options.profile, results }, null, 2));
} else {
  for (const r of results) {
    console.log(`[${r.loaded && !r.fatal.length ? "PASS" : "FAIL"}] ${r.map.padEnd(10)} loaded=${r.loaded} fatal=${r.fatal.length} (${r.secs}s, ${r.why})`);
    for (const line of r.fatal) console.log(`       ${line}`);
  }
  console.log(`summary: ${results.length - failed.length}/${results.length} maps loaded`);
}
process.exitCode = failed.length ? 1 : 0;
