# cleanboost (npm)

This folder packages CleanBoost for the **npm registry**. `npm install -g cleanboost`
downloads a single pre-built native binary to `~/.cleanboost/bin/` and wires five
case-insensitive command names for convenience:

```bash
$ npm install -g cleanboost
$ cleanboost --version        # or:
$ CleanBoost --version        # all equivalent on macOS + Windows
$ CLEANBOOST --version
$ cleanboost-cli --version
$ cb --version
```

## Requirements

- Node.js **18+** (for running the postinstall launcher; not for using the binary)
- macOS (Intel or Apple Silicon, one universal binary) **or** Windows 10/11 (x64; arm64 also supported)
- ~50 MB of disk for the downloaded prebuilt binary

Linux is **explicitly excluded** (matches the project's README).

## What postinstall does

1. Detects your OS + arch.
2. Downloads `cleanboost-<version>-{darwin-universal|windows-x64|windows-arm64}.{tar.gz|zip}`
   from `https://github.com/FCO-inc/CleanBoost/releases`.
3. Extracts it to `~/.cleanboost/bin/cleanboost{,.exe}`.
4. `chmod 755` on macOS.

Idempotent: if `~/.cleanboost/bin/cleanboost` already exists, postinstall skips
the download. To force re-download, `rm -rf ~/.cleanboost` and reinstall.

## Manual / portable install

If you don't want to use npm, grab the same archive directly:

- macOS: <https://github.com/FCO-inc/CleanBoost/releases/latest>
- Windows: same URL, pick `.exe.zip`

## Custom install location

```bash
export CLEANBOOST_HOME=/some/path     # before `npm install -g cleanboost`
```

The binary will land in `$CLEANBOOST_HOME/bin/` and the shim will look for it there.

## Uninstall

```bash
npm uninstall -g cleanboost
```

Removes the shim from your npm prefix AND `~/.cleanboost`.

## License

MIT — see ../LICENSE at the repo root.
