#!/usr/bin/env node

import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const server = process.argv[2] ? resolve(process.argv[2]) : "";
if (!server || !existsSync(server)) {
  process.stderr.write("Usage: server-runner.mjs /absolute/path/to/MCP-server.js\n");
  process.exit(2);
}

// SDK 1.12's stdio server installs a data listener without retaining an active
// event-loop handle. Under this non-interactive WSL launch path the process can
// therefore exit between spawn and initialize. Keep it alive; the client
// transport terminates the runner after closing stdin.
setInterval(() => {}, 60_000);
const stdinOn = process.stdin.on.bind(process.stdin);
process.stdin.on = (event, listener) => {
  if (event === "end" || event === "close") return process.stdin;
  return stdinOn(event, listener);
};

// Larger v6c loads can exceed the backend's 60 * 700 ms startup poll. Extend
// its exported I/O adapter before importing the server. Keep the registry's
// process ownership, log capture, failed-launch cleanup and PID handshake.
const startupMs = Number(process.env.UH_ZANDRONUM_STARTUP_TIMEOUT_MS || 120000);
if (!Number.isFinite(startupMs) || startupMs < 42000 || startupMs > 600000) {
  throw Error("UH_ZANDRONUM_STARTUP_TIMEOUT_MS must be between 42000 and 600000");
}
const registryPath = join(dirname(server), "process/registry.js");
const launchPath = join(dirname(server), "process/launch.js");
if (!existsSync(registryPath) || !existsSync(launchPath)) {
  throw Error("MCP backend must provide process/registry.js and process/launch.js");
}
const [{ defaultLaunchIo }, { waitForPort }] = await Promise.all([
  import(pathToFileURL(registryPath)), import(pathToFileURL(launchPath)),
]);
if (!defaultLaunchIo || typeof waitForPort !== "function") {
  throw Error("MCP backend does not expose the startup I/O adapter");
}
defaultLaunchIo.waitForPort = (host, port) =>
  waitForPort(host, port, Math.ceil(startupMs / 700) + 1, 700);
await import(pathToFileURL(server));
