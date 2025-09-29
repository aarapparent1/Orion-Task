import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Orion Memory API URL (your deployed backend)
ORION_API = "https://orion-memory.onrender.com"

st.set_page_config(page_title="Orion Demo Suite", layout="wide")

st.title("🧠 Orion AI Demo Suite")

# Sidebar navigation
page = st.sidebar.radio("Navigate", ["Orion Memory", "Task Manager"])


# ================================================================
# ORION MEMORY TAB
# ================================================================
if page == "Orion Memory":
    st.header("📚 Orion Memory")

    st.subheader("Book Mode (Feed Orion)")
    text = st.text_area("Paste text for Orion to remember")
    if st.button("Remember"):
        if text.strip():
            sentences = [s.strip() for s in text.split(".") if s.strip()]
            stored = 0
            for s in sentences:
                payload = {"user_id": "demo", "fact": s}
                try:
                    r = requests.post(f"{ORION_API}/fact", json=payload)
                    if r.status_code == 200:
                        stored += 1
                except Exception as e:
                    st.error(f"Error storing fact: {e}")
            # also save a summary fact
            summary = f"Summary: {sentences[0]} ... ({len(sentences)} facts total)"
            requests.post(f"{ORION_API}/fact", json={"user_id": "demo", "fact": summary})
            st.success(f"Stored {stored} facts + 1 summary from Book Mode.")
        else:
            st.warning("Please enter some text.")

    st.subheader("🔍 Recall")
    query = st.text_input("Ask Orion", placeholder="e.g. What is Orion?")
    if st.button("Recall"):
        try:
            r = requests.get(f"{ORION_API}/provenance/demo")
            if r.status_code == 200:
                data = r.json()
                results = []
                for f in data:
                    fact = f.get("fact", "")
                    source = f.get("source", "unknown")
                    ts = f.get("timestamp", "")[:19]

                    # ✅ Loose keyword match
                    if not query or any(word in fact.lower() for word in query.lower().split()):
                        results.append(f"- **{fact}**  _(source: {source}, time: {ts})_")

                if results:
                    st.markdown("\n".join(results))
                else:
                    st.info("No exact matches. Here’s everything Orion remembers:")
                    for f in data:
                        fact = f.get("fact", "")
                        source = f.get("source", "unknown")
                        ts = f.get("timestamp", "")[:19]
                        st.write(f"- **{fact}**  _(source: {source}, time: {ts})_")
            else:
                st.error("Failed to reach Orion Memory API.")
        except Exception as e:
            st.error(f"Error: {e}")

    if st.button("Clear Memory"):
        try:
            r = requests.post(f"{ORION_API}/clear/demo")
            if r.status_code == 200:
                st.success("Memory cleared for demo user.")
            else:
                st.error("Failed to clear memory.")
        except Exception as e:
            st.error(f"Error: {e}")


# ================================================================
# TASK MANAGER TAB
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

        # Summarize tasks (local AI-like)
        if st.button("Summarize Tasks"):
            task_texts = [t["task"] for t in tasks]
            if task_texts:
                summary = f"This project has {len(task_texts)} tasks. " \
                          f"Focus: {', '.join(task_texts[:3])}" + ("..." if len(task_texts) > 3 else "")
                st.success(summary)
                # save summary into Orion Memory
                try:
                    requests.post(f"{ORION_API}/fact", json={"user_id": "demo", "fact": f"Task summary: {summary}"})
                except:
                    pass
            else:
                st.info("No tasks to summarize.")

        if st.button("Clear Tasks"):
            st.session_state["projects"][project] = []
            st.success(f"Cleared tasks for {project}")
