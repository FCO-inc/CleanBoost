#!/usr/bin/env node
'use strict';

/**
 * cleanboost stub — postinstall confirmation.
 *
 * This package is a thin alias around the real `cleenboost` npm package.
 * The Python binary download itself is handled by cleenboost's own
 * postinstall (it knows the actual GitHub Releases URL and platform
 * detection logic). We just print a friendly confirmation so the user
 * sees what happened, and so they can verify the alias plumbing worked.
 *
 * Failure here is NON-FATAL: the real cleenboost postinstall runs
 * independently in its own subdirectory and will still download the
 * binary even if this script can't locate the dependency on disk for
 * some reason (very rare — e.g. read-only sandbox before the file move).
 */

const path = require('node:path');

function log(msg)  { process.stdout.write(`[cleanboost] ${msg}\n`); }
function warn(msg) { process.stderr.write(`[cleanboost] ${msg}\n`); }

let realPkgDir;
try {
  // Resolve `cleenboost/package.json` to confirm the dependency was installed
  // by npm into this stub's node_modules/ tree.
  realPkgDir = path.dirname(require.resolve('cleenboost/package.json'));
  log('alias installed — underlying package located at:');
  log('  ' + realPkgDir);
  log('The `cleanboost` binary is now resolvable on your PATH.');
  log('Verify with:  cleanboost --version');
  log('The actual binary download happens via cleenboost\'s own postinstall');
  log('(one-time network call to GitHub Releases).');
} catch (err) {
  warn('Could not resolve the `cleenboost` dependency on disk after install.');
  warn('This is non-fatal — retry with: npm install -g cleanboost --force');
  warn('Diagnostic: ' + (err && err.message ? err.message : String(err)));
  // Non-fatal: do NOT exit non-zero. npm lets the install proceed and
  // the user's next `cleanboost --version` will surface the real error
  // with a much more useful stack trace than we could fabricate here.
  process.exit(0);
}
