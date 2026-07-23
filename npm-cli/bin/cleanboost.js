#!/usr/bin/env node
/**
 * cleanboost — launcher shim.
 * npm wires 5 bin names (cleanboost, cleanboost-cli, cb, CleanBoost, CLEANBOOST)
 * to this script. We forward args to the actual prebuilt binary that
 * postinstall downloaded to ~/.cleanboost/bin/.
 */
'use strict';

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { spawn } = require('node:child_process');

const exeName = os.platform() === 'win32' ? 'cleanboost.exe' : 'cleanboost';
const installRoot = process.env.CLEANBOOST_HOME || path.join(os.homedir(), '.cleanboost');
const exePath = path.join(installRoot, 'bin', exeName);

if (!fs.existsSync(exePath)) {
  console.error(`[cleanboost] binary not found at ${exePath}`);
  console.error('[cleanboost] The postinstall script may have failed.');
  console.error('[cleanboost] Reinstall: npm install -g cleanboost');
  console.error('[cleanboost] Manual:    https://github.com/freebuff/cleanboost/releases');
  process.exit(1);
}

const child = spawn(exePath, process.argv.slice(2), {
  stdio: 'inherit',
  windowsHide: false,
});

child.on('exit', (code, signal) => {
  if (signal) {
    try { process.kill(process.pid, signal); } catch (_) { /* ignore */ }
    return;
  }
  process.exit(code ?? 0);
});
child.on('error', (err) => {
  console.error(`[cleanboost] failed to launch: ${err.message}`);
  process.exit(1);
});
