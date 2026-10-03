import sys
import time
from pathlib import Path

SKIP_EXT = {".crdownload", ".tmp", ".part", ".download", ".ini"}
MIN_AGE_SECONDS = 300  # skip files modified in the last 5 minutes


def scan_folder(folder):
    """Return a list of files directly inside `folder` that are safe to sort."""
    files = []
    now = time.time()
    for p in Path(folder).iterdir():
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        if p.suffix.lower() in SKIP_EXT:
            continue
        if now - p.stat().st_mtime < MIN_AGE_SECONDS:
            continue
        files.append(p)
    return sorted(files)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else Path.home() / "Downloads"
    found = scan_folder(target)
    print(f"Found {len(found)} files in {target}")
    for f in found[:20]:
        print(" -", f.name)