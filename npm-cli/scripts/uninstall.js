#!/usr/bin/env node
/**
 * uninstall for cleanboost.
 * Best-effort removal of the locally-installed binary directory.
 * (npm-managed bin shims are removed automatically by npm itself.)
 *
 * SAFETY: we only ever delete paths we can prove belong to cleanboost.
 * If CLEANBOOST_HOME is overridden to an unrelated directory (e.g. ~ or
 * /usr/local/bin by accident), we refuse to remove it and print instructions.
 */
'use strict';

const fs   = require('node:fs');
const path = require('node:path');
const os   = require('node:os');

const exeName = os.platform() === 'win32' ? 'cleanboost.exe' : 'cleanboost';

function looksLikeOurs(rootPath) {
  // Default install location is always safe: ~/.cleanboost.
  const defaultRoot = path.join(os.homedir(), '.cleanboost');
  if (rootPath === defaultRoot) return true;

  // Custom CLEANBOOST_HOME: only safe if (a) the binary we installed is there, AND
  // (b) the path itself contains "cleanboost" so we don't accidentally delete /usr/local/bin.
  const sentinel = path.join(rootPath, 'bin', exeName);
  if (!fs.existsSync(sentinel)) return false;

  return rootPath.toLowerCase().includes('cleanboost');
}

const installRoot = process.env.CLEANBOOST_HOME || path.join(os.homedir(), '.cleanboost');

if (!fs.existsSync(installRoot)) {
  process.stdout.write(`[cleanboost] nothing to remove at ${installRoot}\n`);
  process.exit(0);
}

if (!looksLikeOurs(installRoot)) {
  // Refuse. Don't exit non-zero — npm treats non-zero from uninstall as fatal.
  console.error(`[cleanboost] Refusing to remove ${installRoot}:`);
  console.error('[cleanboost]   - It is not the default ~/.cleanboost');
  console.error('[cleanboost]   - It does not contain a cleanboost installation we placed');
  console.error('[cleanboost] To remove manually:');
  console.error(`[cleanboost]   rm -rf "${installRoot}"`);
  process.exit(0);
}

fs.rmSync(installRoot, { recursive: true, force: true });
process.stdout.write(`[cleanboost] removed ${installRoot}\n`);
