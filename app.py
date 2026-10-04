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
HISTORY = Path("history.json")

st.set_page_config(page_title=APP_NAME, page_icon="📁", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"], .stApp {font-family: 'DM Sans', sans-serif;}
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 2rem; padding-bottom: 5rem; max-width: 1250px;}
[data-testid="stSidebar"] {background: #EFE8D8; border-right: 1px solid #DDD4C0;}
.brand {font-family: 'Fraunces', serif; font-size: 30px; font-weight: 700; color: #B5482A; margin-bottom: 1rem;}
.eyebrow {font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: #8A806C; margin: 1.2rem 0 .4rem 0;}
.hist {font-size: 14px; padding: 6px 2px; color: #3B352B;}
.hist span {font-size: 12px; color: #8A806C;}
.title {font-family: 'Fraunces', serif; font-size: 34px; font-weight: 600; line-height: 1.1;}
.sub {font-size: 13px; color: #7A705F; margin: .3rem 0 1rem 0;}
.fname {font-weight: 700; font-size: 15px;}
.reason {font-size: 12px; color: #7A705F; margin-top: 2px;}
.warn {color: #B5482A; font-weight: 700;}
.pbox {padding: 14px; border-radius: 10px; background: #F6F1E7; font-size: 13px; line-height: 1.55;
       color: #4A4336; white-space: pre-wrap; word-break: break-word;}
.pname {font-weight: 700; font-size: 16px; margin-bottom: .6rem;}
.pwhy {font-size: 13px; line-height: 1.5; color: #4A4336;}
.banner {padding: 16px 20px; border-radius: 12px; background: #E7F2E8; border: 1px solid #BCD9C0; margin: 1rem 0;}
.banner b {color: #1F5A33; font-size: 15px;} .banner div {color: #3F7A55; font-size: 13px; margin-top: 2px;}
.fcard {padding: 14px 16px; border-radius: 10px; background: #FFFCF5; border: 1px solid #E4DBC6; margin-bottom: 10px;}
.fcard span {font-size: 13px; color: #7A705F;}
div[data-testid="stVerticalBlockBorderWrapper"] {background: #FFFCF5; border-color: #E4DBC6 !important; border-radius: 10px;}
.stButton > button {border-radius: 8px; font-weight: 700;}
.statusbar {position: fixed; left: 0; right: 0; bottom: 0; height: 40px; background: #EFE8D8;
            border-top: 1px solid #DDD4C0; display: flex; align-items: center; padding: 0 24px;
            font-size: 13px; color: #5C5446; z-index: 999;}
.dot {width: 7px; height: 7px; border-radius: 50%; background: #3FA66B; margin-right: 8px; display: inline-block;}
</style>
""",
    unsafe_allow_html=True,
)


def load_history():
    try:
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    except Exception:
        return []


def add_history(count):
    items = load_history()
    items.append({"when": datetime.now().strftime("%d %b, %I:%M %p"), "count": count})
    HISTORY.write_text(json.dumps(items[-20:], indent=2), encoding="utf-8")


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


cats = load_categories()
for key, val in {"folder": "test_folder", "plan": None, "done": None, "sel": 0, "scan_id": 0, "msg": None}.items():
    st.session_state.setdefault(key, val)

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(f'<div class="brand">{APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Locations</div>', unsafe_allow_html=True)
    for name in ("Downloads", "Documents", "Desktop"):
        st.button(name, key=f"loc_{name}", on_click=set_folder, args=(Path.home() / name,), width="stretch")
    st.markdown('<div class="eyebrow">History</div>', unsafe_allow_html=True)
    hist = load_history()
    if not hist:
        st.markdown('<div class="hist"><span>No runs yet</span></div>', unsafe_allow_html=True)
    for h in reversed(hist[-4:]):
        st.markdown(f'<div class="hist">{h["when"]}<br><span>{h["count"]} files sorted</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Safety</div>', unsafe_allow_html=True)
    st.button("Undo last move", on_click=do_undo, width="stretch")

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
        "<div>Nothing was deleted or overwritten. Use Undo in the sidebar to put everything back.</div></div>",
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
        "Nothing moves until you apply.</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    f'<div class="statusbar"><span class="dot"></span>Offline · {MODEL}</div>',
    unsafe_allow_html=True,
)