import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime

# ---------------------------------
# Config
# ---------------------------------
ORION_API = "https://orion-memory.onrender.com"

st.set_page_config(page_title="Orion AI Demo Suite", layout="wide")
st.title("🧠 Orion AI Demo Suite")

page = st.sidebar.radio("Navigate", ["Orion Memory", "Task Manager"])


# ---------------------------------
# Helpers
# ---------------------------------
def call_orion(path: str, method: str = "GET", payload: dict | None = None):
    url = f"{ORION_API}/{path}"
    try:
        if method == "GET":
            r = requests.get(url, params=payload)
        elif method == "POST":
            r = requests.post(url, json=payload)
        else:
            return {"error": "invalid method"}
        if r.status_code == 200:
            return r.json()
        return {"error": f"{r.status_code}: {r.text}"}
    except Exception as e:
        return {"error": str(e)}


def split_sentences(text: str) -> list[str]:
    # simple sentence splitter: split on . ! ?
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]


# ================================================================
# ORION MEMORY
# ================================================================
if page == "Orion Memory":
    st.header("📚 Orion Memory")

    # --- Quick Fact Entry ---
    st.subheader("Quick Fact")
    fact = st.text_input("Enter a single fact for Orion to remember")
    col_qf1, col_qf2 = st.columns([1, 1])
    with col_qf1:
        if st.button("Save Fact"):
            if fact.strip():
                resp = call_orion("fact", "POST", {"user_id": "demo", "fact": fact.strip()})
                if isinstance(resp, dict) and "error" not in resp:
                    st.success("Fact saved.")
                else:
                    st.error(f"Failed to save fact. {resp}")
            else:
                st.warning("Please enter something first.")
    with col_qf2:
        if st.button("Clear Memory"):
            resp = call_orion("clear/demo", "POST")
            if isinstance(resp, dict) and "error" not in resp:
                st.success("All memory cleared for demo user.")
            else:
                st.error(f"Failed to clear memory. {resp}")

    st.markdown("---")

    # --- Book Mode ---
    st.subheader("Book Mode (Paste multiple sentences)")
    text = st.text_area("Paste text for Orion to remember (it will split into sentences and add a summary)", height=180)
    if st.button("Remember (Book Mode)"):
        if text.strip():
            sentences = split_sentences(text)
            stored = 0
            for s in sentences:
                resp = call_orion("fact", "POST", {"user_id": "demo", "fact": s, "source": "book_mode"})
                if isinstance(resp, dict) and "error" not in resp:
                    stored += 1
            # add a simple summary fact (first 2 sentences)
            if sentences:
                summary = " ".join(sentences[:2]) if len(sentences) > 1 else sentences[0]
                _ = call_orion("fact", "POST", {
                    "user_id": "demo",
                    "fact": f"Summary: {summary}",
                    "source": "book_mode_summary"
                })
            st.success(f"Stored {stored} facts + 1 summary from Book Mode.")
        else:
            st.warning("Please paste some text.")

    st.markdown("---")

    # --- Recall (fixed) ---
    st.subheader("🔍 Recall")
    query = st.text_input("Ask Orion (e.g., What is Orion?)")
    if st.button("Recall"):
        data = call_orion("provenance/demo", "GET")
        if isinstance(data, list) and data:
            results = []

            # 1. Exact/substring match first
            for f in data:
                fact_text = f.get("fact", "")
                source = f.get("source", "unknown")
                ts = f.get("timestamp", "")[:19]
                if query and query.lower() in fact_text.lower():
                    results.append(f"- **{fact_text}**  _(source: {source}, time: {ts})_")

            # 2. If no results, try keyword match
            if not results and query:
                for f in data:
                    fact_text = f.get("fact", "")
                    if any(word in fact_text.lower() for word in query.lower().split()):
                        results.append(f"- **{fact_text}**")

            # 3. Fallback if still nothing
            if results:
                st.markdown("\n".join(results))
            else:
                st.info("No direct matches. Here’s everything Orion remembers:")
                for f in data:
                    fact_text = f.get("fact", "")
                    source = f.get("source", "unknown")
                    ts = f.get("timestamp", "")[:19]
                    st.write(f"- **{fact_text}**  _(source: {source}, time: {ts})_")
        else:
            st.info("No memory found yet (or the API is unreachable).")

    # --- Summarize Facts ---
    if st.button("Summarize Facts"):
        data = call_orion("provenance/demo", "GET")
        if isinstance(data, list) and data:
            facts = [f.get("fact", "") for f in data if f.get("fact")]
            if facts:
                highlights = ", ".join(facts[:3]) + ("..." if len(facts) > 3 else "")
                st.success(f"Orion currently remembers {len(facts)} facts. Highlights: {highlights}")
            else:
                st.info("No facts to summarize.")
        else:
            st.info("No facts found.")


# ================================================================
# TASK MANAGER (unchanged)
# ================================================================
if page == "Task Manager":
    st.header("✅ Orion Task Manager")

    if "projects" not in st.session_state:
        st.session_state["projects"] = {}
        st.session_state["active_project"] = None

    # Create new project
    new_proj = st.text_input("New Project Name")
    if st.button("Create Project"):
        if new_proj:
            st.session_state["projects"][new_proj] = []
            st.session_state["active_project"] = new_proj
            st.success(f"Project created: {new_proj}")

    # Select active project
    if st.session_state["projects"]:
        project = st.selectbox(
            "Select Project",
            options=list(st.session_state["projects"].keys()),
            index=list(st.session_state["projects"].keys()).index(st.session_state["active_project"]) if st.session_state["active_project"] else 0
        )
        st.session_state["active_project"] = project

        # Add task
        task_desc = st.text_input("Task Description")
        if st.button("Add Task"):
            if task_desc:
                st.session_state["projects"][project].append(
                    {"task": task_desc, "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                )
                st.success(f"Task added to {project}")

        # List tasks
        tasks = st.session_state["projects"][project]
        if tasks:
            df = pd.DataFrame(tasks)
            st.table(df)
        else:
            st.info("No tasks yet.")

        # Summarize tasks
        if st.button("Summarize Tasks"):
            task_texts = [t["task"] for t in tasks]
            if task_texts:
                summary = (
                    f"This project has {len(task_texts)} tasks. "
                    f"Focus: {', '.join(task_texts[:3])}" + ("..." if len(task_texts) > 3 else "")
                )
                st.success(summary)
                try:
                    _ = requests.post(f"{ORION_API}/fact", json={"user_id": "demo", "fact": f"Task summary: {summary}"})
                except:
                    pass
            else:
                st.info("No tasks to summarize.")

        # Clear tasks
        if st.button("Clear Tasks"):
            st.session_state["projects"][project] = []
            st.success(f"Cleared tasks for {project}")
