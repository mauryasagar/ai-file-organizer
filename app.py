import html
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from classifier import MODEL, classify, load_categories
from extractor import extract_text
from organizer import LOG_NAME, apply_plan, undo
from scanner import scan_folder

APP_NAME = "Organizr"
LOGO = "🗁"
HISTORY = Path("history.json")
STYLE = Path(__file__).parent / "static" / "style.css"

st.set_page_config(page_title=APP_NAME, page_icon="📁", layout="wide", initial_sidebar_state="expanded")

st.markdown(f"<style>{STYLE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def load_history():
    try:
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    except Exception:
        return []


def add_history(count):
    items = load_history()
    items.append({"when": datetime.now().strftime("%d %b, %I:%M %p"), "count": count})
    HISTORY.write_text(json.dumps(items[-20:], indent=2), encoding="utf-8")


def clear_history():
    HISTORY.write_text("[]", encoding="utf-8")


def set_folder(path):
    st.session_state.folder = str(path)


def select_row(i):
    st.session_state.sel = i


def do_undo():
    folder = st.session_state.folder
    if (Path(folder) / LOG_NAME).exists():
        undo(folder)
        st.session_state.msg = "Undo complete. Files restored."
    else:
        st.session_state.msg = "Nothing to undo."
    st.session_state.plan = None
    st.session_state.done = None


def render_menu(prefix):
    """Menu content, used in the desktop sidebar and the mobile popover."""
    st.markdown('<div class="eyebrow">Locations</div>', unsafe_allow_html=True)
    for name in ("Downloads", "Documents", "Desktop"):
        st.button(name, key=f"{prefix}_loc_{name}", on_click=set_folder, args=(Path.home() / name,), width="stretch")
    st.markdown('<div class="eyebrow">History</div>', unsafe_allow_html=True)
    hist = load_history()
    if not hist:
        st.markdown('<div class="hist"><span>No runs yet</span></div>', unsafe_allow_html=True)
    for h in reversed(hist[-4:]):
        st.markdown(f'<div class="hist">{h["when"]}<br><span>{h["count"]} files sorted</span></div>', unsafe_allow_html=True)
    if hist:
        st.button("Clear history", key=f"{prefix}_clear", type="tertiary", on_click=clear_history)
    st.markdown('<div class="eyebrow">Safety</div>', unsafe_allow_html=True)
    st.button("Undo last move", key=f"{prefix}_undo", on_click=do_undo, width="stretch")
    st.markdown(
        f'<div class="statusbar"><span class="dot"></span>Offline · {MODEL}</div>',
        unsafe_allow_html=True,
    )


cats = load_categories()
for key, val in {"folder": "test_folder", "plan": None, "done": None, "sel": 0, "scan_id": 0, "msg": None}.items():
    st.session_state.setdefault(key, val)

BRAND = f'<a class="brand" href="/" target="_self">{LOGO} {APP_NAME}</a>'

# ---------- Sidebar (desktop) ----------
with st.sidebar:
    st.markdown(BRAND, unsafe_allow_html=True)
    st.markdown('<div class="privacy">Runs on your laptop. Nothing is uploaded.</div>', unsafe_allow_html=True)
    render_menu("sb")

# ---------- Top bar (phone and tablet) ----------
with st.container(key="mobilebar"):
    bar_l, bar_r = st.columns([1, 1], vertical_alignment="center")
    bar_l.markdown(BRAND, unsafe_allow_html=True)
    with bar_r.popover("☰ Menu"):
        st.markdown('<div class="privacy">Runs on your laptop. Nothing is uploaded.</div>', unsafe_allow_html=True)
        render_menu("mb")

# ---------- Header ----------
folder = st.session_state.folder
st.markdown(f'<div class="title">{html.escape(Path(folder).name or folder)}</div>', unsafe_allow_html=True)
c1, c2 = st.columns([4, 1.2], vertical_alignment="bottom")
c1.text_input("Folder", key="folder", label_visibility="collapsed")
scan = c2.button("Scan and plan", type="primary", width="stretch")

if scan:
    folder = st.session_state.folder
    if not Path(folder).is_dir():
        st.error("Folder not found.")
    else:
        files = scan_folder(folder)
        if not files:
            st.warning("No files to sort in this folder.")
        else:
            bar = st.progress(0, text="Starting local Gemma...")
            plan = []
            for i, f in enumerate(files):
                bar.progress(i / len(files), text=f"Reading {f.name} ({i + 1}/{len(files)})")
                text = extract_text(f)
                cat, reason = classify(f.name, text, cats)
                plan.append({"file": str(f), "category": cat, "reason": reason, "preview": text[:500]})
            bar.empty()
            st.session_state.scan_id += 1
            st.session_state.plan = plan
            st.session_state.done = None
            st.session_state.sel = 0
            st.session_state.msg = None

if st.session_state.msg:
    st.info(st.session_state.msg)

plan = st.session_state.plan
done = st.session_state.done

# ---------- Done view ----------
if done:
    st.markdown(
        f'<div class="banner"><b>Moved {done["count"]} files into {len(done["groups"])} folders</b>'
        "<div>Nothing was deleted or overwritten. Use Undo in the menu to put everything back.</div></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for n, (cat, names) in enumerate(done["groups"].items()):
        cols[n % 2].markdown(
            f'<div class="fcard"><b>{html.escape(cat)}</b><br><span>{html.escape(", ".join(names))}</span></div>',
            unsafe_allow_html=True,
        )

# ---------- Plan view ----------
elif plan:
    sid = st.session_state.scan_id
    review = sum(1 for p in plan if p["category"] == "Other")
    main, side = st.columns([2.3, 1.2], gap="large")

    with main:
        a, b = st.columns([3, 1.4], vertical_alignment="center")
        a.markdown(
            f'<div class="sub">{len(plan)} files · {len(plan) - review} sorted with confidence · {review} need review</div>',
            unsafe_allow_html=True,
        )
        if b.button(f"Apply {len(plan)} moves", type="primary", width="stretch"):
            groups = {}
            for i, item in enumerate(plan):
                item["category"] = st.session_state.get(f"cat_{sid}_{i}", item["category"])
                groups.setdefault(item["category"], []).append(Path(item["file"]).name)
            moves = apply_plan(st.session_state.folder, plan)
            add_history(len(moves))
            st.session_state.done = {"count": len(moves), "groups": groups}
            st.session_state.plan = None
            st.rerun()

        for i, p in enumerate(plan):
            with st.container(border=True):
                x, y, z = st.columns([3, 2, 0.9], vertical_alignment="center")
                mark = "● " if i == st.session_state.sel else ""
                note = '<span class="warn">Please check this one. </span>' if p["category"] == "Other" else ""
                x.markdown(
                    f'<div class="fname">{mark}{html.escape(Path(p["file"]).name)}</div>'
                    f'<div class="reason">{note}{html.escape(p["reason"])}</div>',
                    unsafe_allow_html=True,
                )
                y.selectbox(
                    "Category",
                    cats,
                    index=cats.index(p["category"]) if p["category"] in cats else 0,
                    key=f"cat_{sid}_{i}",
                    label_visibility="collapsed",
                )
                z.button("View", key=f"view_{sid}_{i}", on_click=select_row, args=(i,), width="stretch")

    with side:
        sel = min(st.session_state.sel, len(plan) - 1)
        item = plan[sel]
        cur = st.session_state.get(f"cat_{sid}_{sel}", item["category"])
        st.markdown('<div class="eyebrow" style="margin-top:0">Preview</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="pname">{html.escape(Path(item["file"]).name)}</div>', unsafe_allow_html=True)
        body = html.escape(item["preview"]) if item["preview"].strip() else "No readable text in this file."
        st.markdown(f'<div class="pbox">{body}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="eyebrow">Why {html.escape(cur)}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="pwhy">{html.escape(item["reason"])}</div>', unsafe_allow_html=True)

# ---------- Empty state ----------
else:
    st.markdown(
        '<div class="sub">Pick a location or paste a folder path, then scan. '
        "Nothing moves until you apply.</div>"
        '<div class="steps">'
        '<div class="step"><i>01</i><b>Scan</b><span>Gemma reads each file locally and decides where it belongs.</span></div>'
        '<div class="step"><i>02</i><b>Review</b><span>Change any category you disagree with before anything moves.</span></div>'
        '<div class="step"><i>03</i><b>Apply</b><span>Nothing is deleted. Undo puts every file back.</span></div>'
        "</div>",
        unsafe_allow_html=True,
    )