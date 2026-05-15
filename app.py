import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.visualization.exporter import (
    DedupGroup,
    AestheticScore,
    export_pipeline_results,
    save_to_json,
)

st.set_page_config(page_title="PhotoTrim Visualizer", layout="wide")

st.title("PhotoTrim Pipeline Visualizer")

with st.sidebar:
    st.header("Pipeline Settings")
    input_dir = st.text_input("Input Directory", value="")
    top_k = st.number_input("Top K", min_value=1, max_value=1000, value=100)
    dhash_threshold = st.number_input("dHash Threshold", min_value=1, max_value=20, value=5)
    clip_threshold = st.number_input("CLIP Threshold", min_value=0.50, max_value=1.0, value=0.92, step=0.01)
    json_output = st.text_input("JSON Output Path (optional)", value="")

    run_button = st.button("Run Pipeline", type="primary")

if run_button:
    if not input_dir or not os.path.isdir(input_dir):
        st.error("Please enter a valid input directory.")
        st.stop()

    with st.spinner("Running pipeline..."):
        try:
            results = export_pipeline_results(
                input_dir,
                top_k=top_k,
                dhash_threshold=dhash_threshold,
                clip_threshold=clip_threshold,
            )
            st.session_state["pipeline_data"] = results

            if json_output:
                save_to_json(results, json_output)
                st.success(f"Results saved to {json_output}")
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            st.stop()

results = st.session_state.get("pipeline_data")

if not results:
    st.info("Configure settings in the sidebar and click **Run Pipeline** to begin.")
    st.stop()

stats = results.get("stats", {})
dedup_groups = results.get("dedup_groups", [])
final_top_k = results.get("final_top_k", [])

st.header("Pipeline Overview")
c1, c2, c3 = st.columns(3)
c1.metric("Input Images", stats.get("input_count", 0))
c2.metric("After Dedup", stats.get("after_dedup", 0), delta=-(stats.get("dedup_removed", 0)))
c3.metric("Final Selected", stats.get("final_count", 0), delta=-(stats.get("aesthetic_removed", 0)))

st.divider()
st.subheader("Deduplication Groups")

multi_groups = [g for g in dedup_groups if len(g.trimmed) > 0]
st.write(f"{len(multi_groups)} groups with duplicates found" if multi_groups else "No duplicate groups detected.")

for g in multi_groups:
    title = (
        f"Group {g.group_id}: 1 kept, {len(g.trimmed)} trimmed "
        f"(similarity: {g.similarity:.4f}, reason: {g.reason})"
    )
    with st.expander(title):
        cols = st.columns([1, 3])
        with cols[0]:
            st.write("**Kept:**")
            kept_name = os.path.basename(g.kept[0]) if g.kept else ""
            st.text(kept_name)
            if g.kept and os.path.exists(g.kept[0]):
                try:
                    st.image(g.kept[0], caption=kept_name, width=200)
                except Exception:
                    pass
        with cols[1]:
            st.write("**Trimmed:**")
            display_trimmed = g.trimmed[:5]
            for tp in display_trimmed:
                tname = os.path.basename(tp)
                st.text(f" - {tname}")
                if os.path.exists(tp):
                    try:
                        st.image(tp, caption=tname, width=150)
                    except Exception:
                        pass
            if len(g.trimmed) > 5:
                st.write(f"... and {len(g.trimmed) - 5} more")

st.divider()
st.subheader("Aesthetic Scores - Top K")

if final_top_k:
    table_data = [
        {"Rank": s.rank, "Filename": os.path.basename(s.path), "Score": round(s.score, 2)}
        for s in final_top_k
    ]
    st.dataframe(table_data, use_container_width=True, hide_index=True)

    st.write("### Top Thumbnails")
    cols_per_row = 5
    thumbnail_paths = [s.path for s in final_top_k[:15]]
    for i in range(0, len(thumbnail_paths), cols_per_row):
        batch = thumbnail_paths[i : i + cols_per_row]
        row_cols = st.columns(len(batch))
        for col, tp in zip(row_cols, batch):
            with col:
                fname = os.path.basename(tp)
                if os.path.exists(tp):
                    try:
                        st.image(tp, caption=f"{fname} ({round([s.score for s in final_top_k if s.path == tp][0], 2)})", use_container_width=True)
                    except Exception:
                        st.text(fname)
                else:
                    st.text(fname)
else:
    st.info("No aesthetic scores available.")
