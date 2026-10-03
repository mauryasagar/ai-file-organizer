import sys
from pathlib import Path

MAX_CHARS = 1000
TEXT_EXT = {".txt", ".md", ".csv", ".json", ".log"}


def extract_text(path):
    """Return the first ~1000 characters of a file's text, or '' if unreadable."""
    path = Path(path)
    ext = path.suffix.lower()
    try:
        if ext in TEXT_EXT:
            return path.read_text(encoding="utf-8", errors="ignore")[:MAX_CHARS]
        if ext == ".pdf":
            import fitz  # pymupdf
            with fitz.open(path) as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
                    if len(text) >= MAX_CHARS:
                        break
                return text[:MAX_CHARS]
        if ext == ".docx":
            import docx
            d = docx.Document(path)
            return "\n".join(p.text for p in d.paragraphs)[:MAX_CHARS]
    except Exception:
        return ""
    return ""


if __name__ == "__main__":
    from scanner import scan_folder
    folder = sys.argv[1] if len(sys.argv) > 1 else "test_folder"
    for f in scan_folder(folder):
        text = extract_text(f).replace("\n", " ")
        print(f"{f.name}: {text[:80]!r}")