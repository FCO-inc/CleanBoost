#!/usr/bin/env node
'use strict';

// Aviso no-bloqueante tras la instalación del stub deprecated.
// El paquete ya no tiene dependencies (era self-ref). Solo informamos.

const realPkg = require(path.join(__dirname, '..', 'package.json'));
const ver = realPkg.version || '?';
process.stdout.write(
  `\n` +
  `  ┌─────────────────────────────────────────────────────────────┐\n` +
  `  │  cleanboost@${ver.padEnd(3, ' ')} (DEPRECATED stub installed)        │\n` +
  `  └─────────────────────────────────────────────────────────────┘\n\n` +
  `  The canonical cleanboost package is now the real CLI itself.\n` +
  `  This stub is kept as a no-op for backward-compatibility and will\n` +
  `  delegate to the real \`cleanboost\` binary if found on PATH.\n\n` +
  `  Recommended:  npm install -g cleanboost@latest\n\n`
);

const path = require('path');
