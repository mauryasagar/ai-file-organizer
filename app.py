from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

from classifier import classify, load_categories
from extractor import extract_text
from organizer import apply_plan, undo
from scanner import scan_folder

ICONS = {
    "Lecture Notes": "📚",
    "Fee Receipts": "🧾",
    "Assignments": "📝",
    "Scholarship Papers": "🎓",
    "Personal": "🏠",
    "Other": "📦",
}

st.set_page_config(page_title="AI File Organizer", page_icon="📁")

st.markdown(
    """
<style>
.hero {padding: 1.4rem 1.6rem; border-radius: 16px;
       background: linear-gradient(135deg, #6C5CE7 0%, #a29bfe 100%);
       margin-bottom: 1.2rem;}
.hero h1 {margin: 0; color: white; font-size: 2rem;}
.hero p {margin: .3rem 0 0 0; color: #f1f0ff;}
.chip {display: inline-block; padding: .35rem .8rem; margin: .2rem .3rem .2rem 0;
       border-radius: 999px; background: #1A1D29; border: 1px solid #6C5CE7;}
.stButton > button {border-radius: 10px;}
</style>
<div class="hero">
  <h1>📁 AI File Organizer</h1>
  <p>Sorts files by what's inside them. Runs fully offline with Gemma via Ollama.</p>
</div>
""",
    unsafe_allow_html=True,
)

cats = load_categories()
folder = st.text_input("Folder to organize", "test_folder")

if st.button("🔍 Scan and plan (nothing is moved)", type="primary"):
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
                cat, reason = classify(f.name, extract_text(f), cats)
                plan.append({"file": str(f), "category": cat, "reason": reason})
            bar.empty()
            st.session_state.plan = plan

plan = st.session_state.get("plan")
if plan:
    counts = Counter(p["category"] for p in plan)
    c1, c2, c3 = st.columns(3)
    c1.metric("Files scanned", len(plan))
    c2.metric("Folders to create", len(counts))
    c3.metric("Needs review", counts.get("Other", 0))

    st.markdown(
        "".join(
            f'<span class="chip">{ICONS.get(c, "📄")} {c}: {n}</span>'
            for c, n in counts.items()
        ),
        unsafe_allow_html=True,
    )

    st.subheader("Proposed plan")
    st.caption("Review it. You can change any category before applying.")
    df = pd.DataFrame(
        [
            {"file": Path(p["file"]).name, "category": p["category"], "reason": p["reason"]}
            for p in plan
        ]
    )
    edited = st.data_editor(
        df,
        column_config={
            "category": st.column_config.SelectboxColumn(options=cats, required=True)
        },
        disabled=["file", "reason"],
        hide_index=True,
        width="stretch",
    )
    if st.button("✅ Apply moves", type="primary"):
        for item, new_cat in zip(plan, edited["category"]):
            item["category"] = new_cat
        moves = apply_plan(folder, plan)
        st.success(f"Moved {len(moves)} files. You can undo below.")
        st.session_state.plan = None

st.divider()
if st.button("↩️ Undo last move"):
    undo(folder)
    st.info("Undo complete. Files restored.")