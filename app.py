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

st.set_page_config(page_title=APP_NAME, page_icon="📁", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700;9..144,800&family=DM+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp {font-family: 'DM Sans', sans-serif; -webkit-font-smoothing: antialiased;}
#MainMenu, footer, header {visibility: hidden;}
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarHeader"] {display: none !important;}

/* ---------- Backdrop (gives the glass something to blur) ---------- */
.stApp {
  background:
    radial-gradient(700px 500px at 8% 12%, rgba(181,72,42,.22), transparent 60%),
    radial-gradient(650px 500px at 92% 18%, rgba(224,170,92,.28), transparent 60%),
    radial-gradient(700px 600px at 70% 95%, rgba(120,150,110,.20), transparent 60%),
    #F6F1E7;
  background-attachment: fixed;
}
[data-testid="stAppViewContainer"], [data-testid="stMain"] {background: transparent !important;}
.block-container {padding-top: 2.4rem; padding-bottom: 6rem; max-width: 1250px;}

/* ---------- Sidebar (frosted) ---------- */
[data-testid="stSidebar"] {
  background: rgba(255,250,240,.55) !important;
  backdrop-filter: blur(22px) saturate(160%);
  -webkit-backdrop-filter: blur(22px) saturate(160%);
  border-right: 1px solid rgba(255,255,255,.7);
  box-shadow: 4px 0 30px rgba(120,90,50,.08);
}
[data-testid="stSidebarUserContent"] {padding-top: 3rem;}
a.brand, a.brand:visited, a.brand:hover {
  font-family: 'Fraunces', serif; font-size: 32px; font-weight: 800; letter-spacing: -.02em;
  background: linear-gradient(135deg, #B5482A, #D9803F);
  -webkit-background-clip: text; background-clip: text; color: transparent !important;
  text-decoration: none !important; display: inline-block; margin-bottom: .6rem;
}
.eyebrow {font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
          color: #9A8D74; margin: 1.5rem 0 .5rem 0;}
.hist {font-size: 14px; font-weight: 600; padding: 8px 12px; color: #3B352B; border-radius: 10px;
       background: rgba(255,255,255,.45); border: 1px solid rgba(255,255,255,.7); margin-bottom: 6px;}
.hist span {font-size: 12px; font-weight: 400; color: #8A806C;}

/* ---------- Typography ---------- */
.title {font-family: 'Fraunces', serif; font-size: 46px; font-weight: 700; letter-spacing: -.025em;
        line-height: 1.05; color: #1F1B16; margin-bottom: .5rem;}
.sub {font-size: 13.5px; font-weight: 500; color: #7A705F; margin: .4rem 0 1rem 0;}
.fname {font-weight: 700; font-size: 15.5px; color: #1F1B16; letter-spacing: -.005em;}
.reason {font-size: 12.5px; color: #7A705F; margin-top: 3px; line-height: 1.45;}
.warn {color: #B5482A; font-weight: 700;}

/* ---------- Glass surfaces ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(255,252,245,.58) !important;
  backdrop-filter: blur(16px) saturate(150%);
  -webkit-backdrop-filter: blur(16px) saturate(150%);
  border: 1px solid rgba(255,255,255,.75) !important;
  border-radius: 16px !important;
  box-shadow: 0 8px 28px rgba(120,90,50,.10), inset 0 1px 0 rgba(255,255,255,.8);
  transition: transform .15s ease, box-shadow .15s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 34px rgba(120,90,50,.16), inset 0 1px 0 rgba(255,255,255,.9);
}
.pbox {padding: 16px; border-radius: 14px; font-size: 13px; line-height: 1.6; color: #4A4336;
       background: rgba(255,252,245,.6); border: 1px solid rgba(255,255,255,.8);
       backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
       box-shadow: 0 6px 22px rgba(120,90,50,.10);
       white-space: pre-wrap; word-break: break-word;
       font-family: ui-monospace, 'Cascadia Code', Consolas, monospace;}
.pname {font-family: 'Fraunces', serif; font-weight: 700; font-size: 20px; letter-spacing: -.01em; margin-bottom: .7rem;}
.pwhy {font-size: 13.5px; line-height: 1.55; color: #4A4336;}
.banner {padding: 18px 22px; border-radius: 16px; margin: 1rem 0;
         background: rgba(226,242,229,.65); border: 1px solid rgba(255,255,255,.8);
         backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
         box-shadow: 0 8px 28px rgba(60,120,80,.12);}
.banner b {color: #1F5A33; font-size: 16px; font-family: 'Fraunces', serif; font-weight: 700;}
.banner div {color: #3F7A55; font-size: 13px; margin-top: 3px;}
.fcard {padding: 16px 18px; border-radius: 16px; margin-bottom: 12px;
        background: rgba(255,252,245,.6); border: 1px solid rgba(255,255,255,.8);
        backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
        box-shadow: 0 8px 26px rgba(120,90,50,.10);}
.fcard b {font-family: 'Fraunces', serif; font-weight: 700; font-size: 17px;}
.fcard span {font-size: 13px; color: #7A705F;}

/* ---------- Inputs ---------- */
div[data-baseweb="input"], div[data-baseweb="select"] > div {
  background: rgba(255,255,255,.62) !important;
  border: 1px solid rgba(255,255,255,.85) !important;
  border-radius: 12px !important;
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 10px rgba(120,90,50,.08);
  font-weight: 500;
}
div[data-baseweb="input"] input {font-weight: 500;}

/* ---------- Buttons ---------- */
.stButton > button {border-radius: 12px; font-weight: 600; letter-spacing: .005em;
                    transition: transform .12s ease, box-shadow .12s ease;}
.stButton > button:hover {transform: translateY(-1px);}
button[kind="secondary"], button[data-testid="stBaseButton-secondary"] {
  background: rgba(255,255,255,.6) !important; border: 1px solid rgba(255,255,255,.9) !important;
  color: #2B261E !important; backdrop-filter: blur(10px);
  box-shadow: 0 2px 10px rgba(120,90,50,.08);
}
button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #C4552F, #A63F22) !important; border: none !important;
  color: #fff !important; box-shadow: 0 6px 18px rgba(181,72,42,.35), inset 0 1px 0 rgba(255,255,255,.25);
}
button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
  box-shadow: 0 10px 24px rgba(181,72,42,.45), inset 0 1px 0 rgba(255,255,255,.3);
}

/* ---------- Status bar ---------- */
.statusbar {position: fixed; left: 0; right: 0; bottom: 0; height: 42px;
            background: rgba(255,250,240,.6); backdrop-filter: blur(18px) saturate(160%);
            -webkit-backdrop-filter: blur(18px) saturate(160%);
            border-top: 1px solid rgba(255,255,255,.75); display: flex; align-items: center;
            padding: 0 24px; font-size: 13px; font-weight: 500; color: #5C5446; z-index: 999;}
.dot {width: 8px; height: 8px; border-radius: 50%; background: #3FA66B; margin-right: 9px; display: inline-block;
      box-shadow: 0 0 0 4px rgba(63,166,107,.22);}
div[data-testid="stVerticalBlockBorderWrapper"] {padding-bottom: 6px;}
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
    st.markdown(
        f'<a class="brand" href="/" target="_self">{LOGO} {APP_NAME}</a>',
        unsafe_allow_html=True,
    )
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