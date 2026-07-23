#!/usr/bin/env node
/**
 * postinstall for cleanboost.
 * Downloads the precompiled binary from GitHub Releases for the current OS/arch
 * and atomically moves it into ~/.cleanboost/bin/.
 *
 * Atomicity: extracts to a temp dir first, then renames the binary into place.
 * If anything fails mid-flight, no half-installed state is left in the user-visible
 * bin dir — re-running `npm install -g cleanboost` is safe to retry.
 */
'use strict';

const https  = require('node:https');
const fs     = require('node:fs');
const path   = require('node:path');
const os     = require('node:os');
const { execSync }   = require('node:child_process');
const { pipeline }   = require('node:stream');
const { promisify }  = require('node:util');

const streamPipeline = promisify(pipeline);

// Extract just "owner/repo" from repository.url — we don't want any scheme prefix
// here because the download URL pattern adds it back. Anything else (ssh://, /path)
// is rejected so we never construct a malformed URL.
const pkg  = require('../package.json');
const REPO_RAW = pkg.repository.url;
let REPO;
if (typeof REPO_RAW === 'string') {
  if (/^git\+https:\/\/github\.com\/([^/]+\/[^/]+?)\.git$/.test(REPO_RAW)) {
    REPO = REPO_RAW.replace(/^git\+https:\/\/github\.com\/([^/]+\/[^/]+?)\.git$/, '$1');
  } else if (/^https:\/\/github\.com\/([^/]+\/[^/]+?)\.git$/.test(REPO_RAW)) {
    REPO = REPO_RAW.replace(/^https:\/\/github\.com\/([^/]+\/[^/]+?)\.git$/, '$1');
  } else if (/^git@github\.com:([^/]+\/[^/]+?)\.git$/.test(REPO_RAW)) {
    REPO = REPO_RAW.replace(/^git@github\.com:([^/]+\/[^/]+?)\.git$/, '$1');
  } else {
    REPO = REPO_RAW;  // fall through; falsy patterns will fail at download time
  }
} else {
  REPO = '';
}
if (!REPO || REPO.includes('://')) {
  console.error(`[cleanboost] unsupported repository.url: ${REPO_RAW}`);
  console.error('[cleanboost] expected git+https://github.com/<owner>/<repo>.git');
  process.exit(1);
}
const VER = pkg.version;

function log(msg)  { process.stdout.write(`[cleanboost] ${msg}\n`); }
function die(msg)  { console.error(`[cleanboost] ${msg}`); process.exit(1); }

/**
 * Detect the asset to download. macOS gets a single universal2 tarball.
 * Windows arm64 falls back to x64 (Windows 11 has built-in Prism x64 emulation,
 * and there is no separate arm64 .zip published yet — fail vs 404).
 */
function detect() {
  const platform = os.platform();
  const arch     = os.arch();

  let asset, binaryName;
  let emulatorHint = '';

  if (platform === 'darwin') {
    asset      = `cleanboost-${VER}-darwin-universal.tar.gz`;
    binaryName = 'cleanboost';
  } else if (platform === 'win32') {
    if (arch === 'ia32') {
      die('CleanBoost does not support 32-bit Windows. Use 64-bit Windows 10/11.');
    }
    if (arch === 'arm64') {
      emulatorHint = ' (Windows arm64 detected; using x64 binary via Prism emulation)';
    }
    asset      = `cleanboost-${VER}-windows-x64.zip`;
    binaryName = 'cleanboost.exe';
  } else {
    die(`CleanBoost does not support ${platform}/${arch}. ` +
        'macOS and Windows 10/11 (64-bit) are supported.');
  }
  return { platform, arch, asset, binaryName, emulatorHint };
}

function download(url, redirectsLeft = 5) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: {
        'User-Agent': 'cleanboost-installer/1.0',
        'Accept':     'application/octet-stream,*/*'
      }
    }, (res) => {
      if ([301, 302, 307, 308].includes(res.statusCode)) {
        res.resume();
        if (redirectsLeft <= 0) return reject(new Error('Too many redirects'));
        const next = res.headers.location;
        if (!next) return reject(new Error(`Redirect missing Location header (${url})`));
        return resolve(download(next, redirectsLeft - 1));
      }
      if (res.statusCode !== 200) {
        return reject(new Error(`HTTP ${res.statusCode} for ${url}`));
      }
      resolve(res);
    });
    req.on('error', reject);
    req.setTimeout(180_000,
      () => req.destroy(new Error(`Download timed out after 180s (${url})`)));
  });
}

async function main() {
  const { platform, arch, asset, binaryName, emulatorHint } = detect();
  const installRoot = process.env.CLEANBOOST_HOME
                    || path.join(os.homedir(), '.cleanboost');
  const binDir   = path.join(installRoot, 'bin');
  const finalBin = path.join(binDir, binaryName);

  log(`detected ${platform}/${arch} → asset=${asset}${emulatorHint}`);

  // Idempotent: skip if a binary is already in place.
  if (fs.existsSync(finalBin)) {
    log(`binary already present at ${finalBin}, left in place. ` +
        `To force reinstall, run: rm -rf "${installRoot}"`);
    return;
  }

  fs.mkdirSync(binDir, { recursive: true });

  const tmpDir      = fs.mkdtempSync(path.join(os.tmpdir(), 'cleanboost-install-'));
  const archivePath = path.join(tmpDir, asset);
  const extractedBin = path.join(tmpDir, binaryName);
  const url = `https://github.com/${REPO}/releases/download/v${VER}/${asset}`;

  try {
    log(`downloading ${url}`);
    const response = await download(url);
    await streamPipeline(response, fs.createWriteStream(archivePath));
    log(`downloaded ${(fs.statSync(archivePath).size / 1024 / 1024).toFixed(1)} MB`);

    log(`extracting to tmp dir ${tmpDir}`);
    // `tar -xf` handles both .tar.gz (mac) and .zip (Windows) on modern OS tar implementations.
    execSync(`tar -xf "${archivePath}" -C "${tmpDir}"`, { stdio: 'inherit' });

    if (!fs.existsSync(extractedBin)) {
      throw new Error(`extracted archive did not contain ${binaryName} at ${extractedBin}`);
    }

    // chmod BEFORE rename — only on non-Windows.
    if (platform !== 'win32') {
      fs.chmodSync(extractedBin, 0o755);
    }

    // Atomic rename into final location. From npm's perspective, either
    // finalBin exists (and is complete) or it doesn't (and we can safely retry).
    fs.renameSync(extractedBin, finalBin);

    log(`installed binary at ${finalBin}`);
    log(`verify with: cleanboost --version`);
  } catch (err) {
    // Clean, actionable error message; no leaked stack trace unless debugging.
    const DEBUG = process.env.CLEANBOOST_DEBUG ? err.stack : null;
    die(`Installation failed: ${err.message}\n` +
        `  • Manual install:    https://github.com/${REPO}/releases/tag/v${VER}\n` +
        `  • Equivalent backup: pipx install cleanboost   (or   pip install --user cleanboost)\n` +
        `  • Bug report:        https://github.com/${REPO}/issues\n` +
        (DEBUG ? `  • Debug:\n${DEBUG}\n` : ''));
  } finally {
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) { /* ignore */ }
  }
}

main().catch((err) => die(err.stack || err.message));
