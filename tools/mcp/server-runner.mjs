#!/usr/bin/env node

import { existsSync } from "node:fs";
import { resolve } from "node:path";
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
await import(pathToFileURL(server));
