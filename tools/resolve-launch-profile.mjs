import { existsSync, readFileSync } from "node:fs";
import { isAbsolute, resolve } from "node:path";

/** Resolve a profile path against the repo root. Absolute paths are kept as-is. */
export function resolveUnderRoot(root, pathValue) {
  if (!pathValue) return pathValue;
  return isAbsolute(pathValue) ? pathValue : resolve(root, pathValue);
}

/** Return a copy of the profile with iwad/files/config resolved under root. */
export function resolveProfilePaths(root, profile) {
  return {
    ...profile,
    iwad: resolveUnderRoot(root, profile.iwad),
    config: profile.config ? resolveUnderRoot(root, profile.config) : profile.config,
    files: (profile.files ?? []).map((file) => resolveUnderRoot(root, file)),
  };
}

/** Load one named profile from a launch JSON and resolve its paths. */
export function loadResolvedProfile(root, profileFile, name) {
  const profiles = JSON.parse(readFileSync(profileFile, "utf8"));
  const raw = profiles?.[name];
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    const available = Object.keys(profiles ?? {});
    throw new Error(
      `unknown profile ${name}${available.length ? ` (available: ${available.join(", ")})` : ""}`,
    );
  }
  const profile = resolveProfilePaths(root, raw);
  const referenced = [profile.iwad, ...(profile.files ?? [])].filter(Boolean);
  const missing = referenced.filter((file) => !existsSync(file));
  if (missing.length) {
    throw new Error(`profile ${name} references missing file(s): ${missing.join(", ")}`);
  }
  return { profile, available: Object.keys(profiles), files: referenced };
}

/** Args for MCP launch_instance from a resolved profile (extraArgs appended by caller). */
export function launchInstanceArgs(instance, profile, extraArgs) {
  const args = {
    instance,
    iwad: profile.iwad,
    files: profile.files,
    map: profile.map,
    fullscreen: profile.fullscreen,
    width: profile.width,
    height: profile.height,
    extraArgs: extraArgs ?? profile.extraArgs,
  };
  return args;
}
