"""GL TRADER - auto updater (STANDALONE).

Runs once at startup (from START_GL_TRADER.bat, before the bot).
It checks the bot's OWN update channel (the public GitHub repo
aihellping-del/gl-trader - only the bot's program files, no user
data) for a newer version:

    version.txt   -> the latest version number
    manifest.txt  -> the list of program files in that version
    checksums.txt -> sha256 of every program file

If a newer version exists, the listed files are downloaded,
hash-verified and copied over the local ones. Hard safety rules:

  * .venv, __pycache__ and the logs folder (the signal history,
    JARVIS_GL_TRADER/logs/signals.json) are NEVER touched, even
    if a manifest listed them.
  * version.txt is written LAST, only after every file copied fine.
  * Any failure (no internet, server down, checksum mismatch)
    prints one short line and exits quietly - an update problem
    must NEVER stop the bot from starting; the old version runs.
  * Set GL_NO_UPDATE=1 to skip the check entirely.

The repo is public, so no token or login is needed to download.
"""

import hashlib
import os
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = "aihellping-del/gl-trader"
BRANCH = "main"
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
ROOT = Path(__file__).resolve().parent  # the GL_TRADER folder itself
TIMEOUT = 6  # seconds - never keep the user waiting

NEVER_TOUCH_DIRS = {".venv", "__pycache__", "logs"}


def _fetch(path):
    headers = {"User-Agent": "GLTrader-Updater"}
    req = urllib.request.Request(RAW + "/" + path, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _parse_checksums(text):
    """checksums.txt: '<sha256>  <path>' per line -> {path: hash}.
    (Right after a release, GitHub's CDN can serve a MIX of new
    and cached-old files - version.txt fresh, a code file stale.
    Verifying every file's hash makes a mixed download abort
    instead of leaving a half-updated install.)"""
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2 and len(parts[0]) == 64:
            out[parts[1].strip()] = parts[0].lower()
    return out


def _fetch_verified(rel, expected_hash):
    """Fetch one file; when a checksum is known, retry a few
    times while the served bytes don't match (CDN settling),
    then give up - the caller aborts the whole update and the
    old version keeps running untouched."""
    attempts = 4 if expected_hash else 1
    last_error = None
    for attempt in range(attempts):
        data = _fetch(rel)
        if not data and not expected_hash:
            # No checksum to verify against: an empty body still
            # means a broken download. WITH a checksum the hash
            # below decides - a legitimately tiny file verifies
            # against its own hash instead of aborting.
            raise ValueError(f"empty download: {rel}")
        if not expected_hash:
            return data
        digest = hashlib.sha256(data).hexdigest()
        if digest == expected_hash:
            return data
        last_error = ValueError(f"checksum mismatch: {rel}")
        if attempt + 1 < attempts:
            time.sleep(2)
    raise last_error


def _version_tuple(text):
    try:
        return tuple(int(p) for p in text.strip().split(".") if p != "")
    except Exception:
        return (0,)


def _local_version():
    try:
        return (ROOT / "version.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


def _is_safe(rel_path):
    parts = Path(rel_path).parts
    if any(p in NEVER_TOUCH_DIRS for p in parts):
        return False
    if ".." in parts or os.path.isabs(rel_path):
        return False
    return True


def main():
    if os.environ.get("GL_NO_UPDATE") == "1":
        return 0
    try:
        remote_version = _fetch("version.txt").decode("utf-8").strip()
    except Exception:
        print("  (Update check nahi ho paya - GL Trader waise hi chalega.)")
        return 0

    local_version = _local_version()
    if _version_tuple(remote_version) <= _version_tuple(local_version):
        return 0  # already up to date - stay silent

    print(f"  Naya GL Trader update mil gaya: v{remote_version} "
          f"(aapke paas v{local_version} hai). Laga raha hu...")
    try:
        manifest = _fetch("manifest.txt").decode("utf-8")
        files = [ln.strip() for ln in manifest.splitlines()
                 if ln.strip() and not ln.strip().startswith("#")]
        try:
            checksums = _parse_checksums(
                _fetch("checksums.txt").decode("utf-8"))
        except Exception:
            checksums = {}  # older channel without checksums
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            staged = []
            for rel in files:
                if not _is_safe(rel) or rel == "version.txt":
                    continue
                data = _fetch_verified(rel, checksums.get(rel))
                dest = tmp / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                staged.append(rel)
            # every download succeeded -> now copy over, version last
            for rel in staged:
                dest = ROOT / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((tmp / rel).read_bytes())
            (ROOT / "version.txt").write_text(
                remote_version + "\n", encoding="utf-8")
        print(f"  Update ho gaya! GL Trader ab v{remote_version} hai.")
    except Exception:
        print("  (Update beech me ruk gaya - purana GL Trader hi chalega. "
              "Agli baar phir try hogi.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
