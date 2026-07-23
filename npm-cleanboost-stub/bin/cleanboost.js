#!/usr/bin/env node
'use strict';

// DEPRECATED redirect stub.
// Originally this package acted as a brand alias for a separately-published
// real implementation. After consolidating all packages under one canonical
// name, this stub has no remaining functional role. It now transparently
// forwards execution to whichever `cleanboost` binary wins on PATH (likely
// the real package installed elsewhere on the system).
//
// Behavior:
//   - If a real `cleanboost` binary exists elsewhere on PATH AND is NOT this
//     very script (different realpath), exec it transparently.
//   - Otherwise print a friendly message explaining the deprecation.

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

function findRealCleanboost() {
  const PATH = (process.env.PATH || '').split(path.delimiter);
  for (const dir of PATH) {
    if (!dir) continue;
    const candidate = path.join(dir, 'cleanboost');
    if (!fs.existsSync(candidate)) continue;
    let real;
    try { real = fs.realpathSync(candidate); } catch { continue; }
    let self;
    try { self = fs.realpathSync(__filename); } catch { self = __filename; }
    if (real === self) continue;
    return candidate;
  }
  return null;
}

const real = findRealCleanboost();
if (real) {
  // Forward transparently to the real cleanboost binary.
  try {
    execFileSync(real, process.argv.slice(2), { stdio: 'inherit' });
    process.exit(0);
  } catch (e) {
    if (typeof e.status === 'number') process.exit(e.status);
    process.exit(1);
  }
}

process.stderr.write(
  'cleanboost@3.1.1 (DEPRECATED stub): the canonical cleanboost package now installs\n' +
  'itself as `cleanboost`. This placeholder is no longer required. To install the\n' +
  'real CLI: `npm install -g cleanboost@latest` and ensure your PATH includes the\n' +
  'npm bin prefix.\n'
);
process.exit(0);
