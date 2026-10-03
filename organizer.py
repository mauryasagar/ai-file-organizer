import json
import shutil
import sys
from pathlib import Path

LOG_NAME = "undo_log.json"


def build_plan(folder, classify_fn, categories):
    """Dry run: return a list of planned moves. Nothing is moved."""
    from scanner import scan_folder
    from extractor import extract_text

    plan = []
    for f in scan_folder(folder):
        cat, reason = classify_fn(f.name, extract_text(f), categories)
        plan.append({"file": str(f), "category": cat, "reason": reason})
    return plan


def _safe_target(dest_dir, name):
    """Never overwrite: add _1, _2... if the name already exists."""
    target = dest_dir / name
    stem, suffix, i = target.stem, target.suffix, 1
    while target.exists():
        target = dest_dir / f"{stem}_{i}{suffix}"
        i += 1
    return target


def apply_plan(folder, plan):
    """Move files into category folders and save an undo log."""
    folder = Path(folder)
    moves = []
    for item in plan:
        src = Path(item["file"])
        if not src.exists():
            continue
        dest_dir = folder / item["category"]
        dest_dir.mkdir(exist_ok=True)
        dst = _safe_target(dest_dir, src.name)
        shutil.move(str(src), str(dst))
        moves.append({"from": str(src), "to": str(dst)})
    (folder / LOG_NAME).write_text(json.dumps(moves, indent=2), encoding="utf-8")
    return moves


def undo(folder):
    """Move everything back to where it came from."""
    log = Path(folder) / LOG_NAME
    if not log.exists():
        print("Nothing to undo.")
        return
    for m in reversed(json.loads(log.read_text(encoding="utf-8"))):
        if Path(m["to"]).exists():
            shutil.move(m["to"], m["from"])
    log.unlink()
    print("Undo complete.")


if __name__ == "__main__":
    from classifier import classify, load_categories

    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    folder = sys.argv[2] if len(sys.argv) > 2 else "test_folder"

    if mode == "undo":
        undo(folder)
    else:
        plan = build_plan(folder, classify, load_categories())
        for p in plan:
            print(f"{Path(p['file']).name} -> {p['category']}")
        if mode == "apply":
            apply_plan(folder, plan)
            print("Done. Run 'python organizer.py undo test_folder' to revert.")
        else:
            print("\nDry run only. Nothing moved. Use 'apply' to move files.")