import json
import sys
from pathlib import Path

import ollama

MODEL = "gemma3:4b"


def load_categories():
    return json.loads(Path("categories.json").read_text(encoding="utf-8"))


def classify(filename, text, categories):
    """Classify by content only. Filename is not sent to the model."""
    prompt = (
        "Classify this file by its CONTENT into exactly one category.\n"
        f"Categories: {categories}\n"
        "Guidance: Fee Receipts = payments, receipts, invoices. "
        "Personal = grocery lists, expense lists, budgets, spreadsheets of personal spending, private notes. "
        "Other = only if nothing else fits.\n\n"
        f"Content: {text[:1000]}\n\n"
        'Reply with JSON only: {"category": "<exact category name>", "reason": "<short reason>"}'
    )
    resp = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        format="json",
    )
    try:
        data = json.loads(resp["message"]["content"])
        cat = data.get("category", "Other")
        if cat not in categories:
            cat = "Other"
        return cat, data.get("reason", "")
    except Exception:
        return "Other", "could not parse model reply"


if __name__ == "__main__":
    from scanner import scan_folder
    from extractor import extract_text

    folder = sys.argv[1] if len(sys.argv) > 1 else "test_folder"
    cats = load_categories()
    for f in scan_folder(folder):
        cat, reason = classify(f.name, extract_text(f), cats)
        print(f"{f.name} -> {cat} ({reason})")