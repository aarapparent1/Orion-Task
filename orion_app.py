import streamlit as st
import requests
import re
from datetime import datetime

# --------------------
# Config
# --------------------
ORION_API = "https://orion-memory.onrender.com"  # your backend on Render

st.set_page_config(page_title="🧠 Orion Demo Suite", layout="wide")

# --------------------
# Helper: Call Orion API
# --------------------
def call_orion(endpoint: str, method: str = "GET", payload: dict = None):
    url = f"{ORION_API}/{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, params=payload)
        elif method == "POST":
            resp = requests.post(url, json=payload)
        else:
            return {"error": "invalid method"}
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"{resp.status_code} {resp.text}"}
    except Exception as e:
        return {"error": str(e)}

# --------------------
# Helper: Split sentences for Book Mode
# --------------------
def split_into_sentences(text: str):
    return re.split(r'(?<=[.!?]) +', text.strip())

# --------------------
# Sidebar
# --------------------
st.sidebar.title("🧭 Orion Demo Suite")
tab_choice = st.sidebar.radio("Choose a demo", ["Orion Memory", "Task Tracker"])

# --------------------
# Tab 1: Orion Memory
# --------------------
if tab_choice == "Orion Memory":
    st.title("🧠 Orion Memory")

    # --- Book Mode
    st.header("📖 Book Mode")
    book_text = st.text_area(
        "Paste a passage. Orion will split it into facts and add a summary.",
        height=200
    )
    if st.button("Remember in Book Mode"):
        if book_text.strip():
            sentences = split_into_sentences(book_text)
            stored_count = 0
            for s in sentences:
                if s.strip():
                    call_orion("fact", "POST", {
                        "user_id": "demo",
                        "fact": s.strip(),
                        "source": "book_mode"
                    })
                    stored_count += 1
            # crude summary = first 2 sentences
            if len(sentences) > 1:
                summary = " ".join(sentences[:2])
                call_orion("fact", "POST", {
                    "user_id": "demo",
                    "fact": f"Summary: {summary}",
                    "source": "book_mode_summary"
                })
            st.success(f"Stored {stored_count} facts + 1 summary")
        else:
            st.warning("Please paste some text first.")

    # --- Recall
    st.header("🔍 Recall")
    query = st.text_input("What should Orion recall?")
    if st.button("Recall"):
        data = call_orion("provenance/demo", "GET")
        if isinstance(data, list) and data:
            results = []
            for f in data:
                fact = f.get("fact", "")
                source = f.get("source", "unknown")
                ts = f.get("timestamp", "")[:19]
                # Loose word match: any word in query appears in fact
                if not query or any(word in fact.lower() for word in query.lower().split()):
                    results.append(f"- **{fact}**  _(source: {source}, time: {ts})_")

            if results:
                st.markdown("\n".join(results))
            else:
                # fallback: show everything
                st.info("No exact matches. Here’s everything Orion remembers:")
                for f in data:
                    fact = f.get("fact", "")
                    source = f.get("source", "unknown")
                    ts = f.get("timestamp", "")[:19]
                    st.write(f"- **{fact}**  _(source: {source}, time: {ts})_")
        else:
            st.info("No memory found or Orion unreachable.")

    # --- Memory Controls
    st.header("🗑️ Memory Management")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Decay Memory"):
            st.write(call_orion("decay/demo", "POST"))
    with col2:
        if st.button("Clear Memory"):
            st.write(call_orion("clear/demo", "POST"))

# --------------------
# Tab 2: Task Tracker
# --------------------
elif tab_choice == "Task Tracker":
    st.title("📋 Orion Task Tracker")

    if "projects" not in st.session_state:
        st.session_state["projects"] = {}
        st.session_state["active_project"] = None

    # --- Project selection
    project = st.text_input("Start a new project")
    if st.button("Create Project"):
        if project:
            st.session_state["projects"][project] = []
            st.session_state["active_project"] = project
            st.success(f"Created project: {project}")

    if st.session_state["projects"]:
        active = st.selectbox(
            "Select a project",
            list(st.session_state["projects"].keys()),
            index=list(st.session_state["projects"].keys()).index(st.session_state["active_project"]) if st.session_state["active_project"] else 0
        )
        st.session_state["active_project"] = active

        # --- Add tasks
        task_desc = st.text_input("New task")
        if st.button("Add Task"):
            if task_desc:
                st.session_state["projects"][active].append(task_desc)
                st.success(f"Added task: {task_desc}")

        # --- Task list
        st.subheader("Tasks")
        if st.session_state["projects"][active]:
            for t in st.session_state["projects"][active]:
                st.write(f"- {t}")
        else:
            st.info("No tasks yet.")

        # --- AI-ish summarizer
        if st.button("Summarize Tasks"):
            tasks = st.session_state["projects"][active]
            if tasks:
                summary = f"{len(tasks)} tasks pending. Next: {tasks[0]}"
                st.success(summary)
            else:
                st.info("No tasks to summarize.")
