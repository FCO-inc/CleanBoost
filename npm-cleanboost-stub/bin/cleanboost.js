#!/usr/bin/env node
'use strict';

/**
 * cleanboost stub — brand-canonical alias for the `cleenboost` npm package.
 *
 * This file is the shim that npm symlinks from <prefix>/bin/cleanboost when
 * the user runs `npm install -g cleanboost`. It forwards every CLI
 * invocation to the real implementation, which lives in the `cleenboost`
 * package's bin script (declared as a runtime dependency in package.json).
 *
 * Why not a copy of the real script?
 *   npm only symlinks bins from top-level globally-installed packages, NOT
 *   from their dependencies. By declaring `bin` here AND listing
 *   `cleenboost` as a dependency, we guarantee:
 *     - `cleanboost` shows up on the user's PATH from THIS package, so
 *       `npm install -g cleanboost` ends with a working CLI even when the
 *       legacy `cleenboost` package was never installed directly.
 *     - The actual code lives in one place (`cleenboost/bin/cleanboost.js`)
 *       and is reused via Node's require resolver — no logic duplication.
 *
 * Defensive: if `cleenboost` is somehow not resolvable (broken install,
 * offline registry race, etc.), we print a clear actionable error and
 * exit non-zero so npm surfaces the failure instead of silently failing.
 */

let realBin;
try {
  // Resolve through the stub's local node_modules — that's where npm puts
  // the `cleenboost` dependency declared in package.json above.
  realBin = require.resolve('cleenboost/bin/cleanboost.js');
} catch (_e) {
  process.stderr.write(
    '[cleanboost] stub package failed to locate the underlying `cleenboost` package.\n' +
    '[cleanboost] This usually means npm could not download the dependency\n' +
    '[cleanboost] (network offline, registry blocked, or a corrupted install).\n' +
    '[cleanboost]\n' +
    '[cleanboost] To recover, run:\n' +
    '[cleanboost]   npm install -g cleenboost --force\n' +
    '[cleanboost] or:\n' +
    '[cleanboost]   npm install -g cleanboost --force\n' +
    '[cleanboost]\n' +
    '[cleanboost] If the problem persists, open an issue at\n' +
    '[cleanboost]   https://github.com/Freebuff/cleanboost/issues\n'
  );
  process.exit(1);
}

// `require()` of the real bin script executes it: cleenboost's bin is a
// Node entry point that locates the prebuilt Python binary in
// ~/.cleanboost/bin/ and execs it with our argv. No state, no callback —
// either it succeeds (process exits via the exec'd binary) or it throws,
// which Node will surface as an uncaught exception with the real script's
// own error messages. Clean delegation.
require(realBin);
