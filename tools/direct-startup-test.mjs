#!/usr/bin/env node

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadResolvedProfile } from "./resolve-launch-profile.mjs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_PROFILES = join(ROOT, "tools/mm8bdm-v6b-linux.launch.json");

function usage() {
  return `Usage: direct-startup-test.mjs [options]

Launch a profile without MCP, require it to stay alive for a short interval,
scan its output for startup fatals, then terminate it cleanly.

Options:
  --profile NAME       profile name (default: mm8bdm-v6b-smoke)
  --duration-sec N     healthy runtime before termination (default: 15)
  --json               emit JSON
  --dry-run            validate paths and print argv only
  --help               show help

Environment: ZANDRONUM_EXE, ZANDRONUM_LAUNCH_PROFILES
`;
}

const options = { profile: "mm8bdm-v6b-smoke", duration: 15, json: false, dryRun: false };
for (let i = 2; i < process.argv.length; i += 1) {
  const arg = process.argv[i];
  if (arg === "--help" || arg === "-h") { console.log(usage()); process.exit(0); }
  if (arg === "--json") { options.json = true; continue; }
  if (arg === "--dry-run") { options.dryRun = true; continue; }
  if (arg === "--profile") { options.profile = process.argv[++i] || ""; continue; }
  if (arg === "--duration-sec") { options.duration = Number.parseInt(process.argv[++i], 10); continue; }
  throw new Error(`unknown option ${arg}`);
}
if (!options.profile || !Number.isInteger(options.duration) || options.duration < 1) throw new Error("invalid option value");

const engine = process.env.ZANDRONUM_EXE;
if (!engine) throw new Error("set ZANDRONUM_EXE to the bridge-patched Zandronum binary");
const profileFile = resolve(process.env.ZANDRONUM_LAUNCH_PROFILES || DEFAULT_PROFILES);
if (!existsSync(engine)) throw new Error(`engine not found: ${engine}`);
if (!existsSync(profileFile)) throw new Error(`profiles not found: ${profileFile}`);
const { profile, files: referenced } = loadResolvedProfile(ROOT, profileFile, options.profile);

const argv = [];
if (profile.config) argv.push("-config", profile.config);
if (profile.iwad) argv.push("-iwad", profile.iwad);
if (profile.files?.length) argv.push("-file", ...profile.files);
if (profile.skill !== undefined) argv.push("-skill", String(profile.skill));
if (profile.map) argv.push("+map", profile.map);
argv.push("+set", "fullscreen", profile.fullscreen ? "1" : "0");
if (profile.width) argv.push("+set", "vid_defwidth", String(profile.width));
if (profile.height) argv.push("+set", "vid_defheight", String(profile.height));
argv.push(...(profile.extraArgs || []));

if (options.dryRun) {
  const out = { status: "dry-run", profile: options.profile, engine, argv, referencedFiles: referenced };
  console.log(options.json ? JSON.stringify(out) : `status=dry-run profile=${options.profile}\nengine=${engine}\nargv=${JSON.stringify(argv)}`);
  process.exit(0);
}

let output = "";
let exited = false;
const child = spawn(engine, argv, {
  cwd: dirname(engine),
  env: { ...process.env, SDL_VIDEODRIVER: process.env.SDL_VIDEODRIVER || "offscreen" },
  stdio: ["ignore", "pipe", "pipe"],
});
for (const stream of [child.stdout, child.stderr]) stream.on("data", (chunk) => { output = `${output}${chunk}`.slice(-200000); });
const early = await new Promise((resolveEarly) => {
  const timer = setTimeout(() => resolveEarly(null), options.duration * 1000);
  child.once("exit", (code, signal) => { exited = true; clearTimeout(timer); resolveEarly({ code, signal }); });
});
if (!exited) {
  child.kill("SIGTERM");
  await Promise.race([new Promise((r) => child.once("exit", r)), new Promise((r) => setTimeout(r, 3000))]);
  if (child.exitCode === null) child.kill("SIGKILL");
}

const fatalLines = output.split(/\r?\n/).filter((line) => /script error|unknown actor|fatal error|cannot find|invalid data encountered|execution could not continue/i.test(line));
const passed = early === null && fatalLines.length === 0;
const result = {
  status: passed ? "pass" : "fail", profile: options.profile, durationSec: options.duration,
  stayedAlive: early === null, earlyExit: early, fatalLines: fatalLines.slice(0, 20),
};
if (options.json) console.log(JSON.stringify(result));
else {
  console.log(`status=${result.status} profile=${result.profile} stayed_alive=${result.stayedAlive} fatal_lines=${result.fatalLines.length}`);
  for (const line of result.fatalLines) console.log(line);
}
process.exitCode = passed ? 0 : 1;
