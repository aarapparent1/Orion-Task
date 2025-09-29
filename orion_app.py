import streamlit as st
import sqlite3
import uuid
from datetime import datetime, date
import requests
import pandas as pd
import matplotlib.pyplot as plt
import textwrap

# Orion API (Render backend)
ORION_API = "https://orion-memory.onrender.com"
USER_ID = "demo"  # fixed for public demo

# ---------------------------
# Helper: Call Orion Memory API
# ---------------------------
def call_orion(endpoint, payload=None, user_id=USER_ID):
    try:
        if endpoint == "recall":
            resp = requests.get(f"{ORION_API}/recall/{user_id}")

        elif endpoint == "remember":  # maps to /fact
            if payload and "content" in payload:
                body = {"user_id": user_id, "fact": payload["content"]}
            else:
                body = {"user_id": user_id, "fact": ""}
            resp = requests.post(f"{ORION_API}/fact", json=body)

        elif endpoint == "summarize":
            resp = requests.get(f"{ORION_API}/summarize/{user_id}")

        elif endpoint == "decay":
            resp = requests.post(f"{ORION_API}/decay/{user_id}")

        else:
            return {"error": f"Unknown endpoint {endpoint}"}

        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception:
                return resp.text
        else:
            return {"error": f"API error: {resp.text}"}

    except Exception as e:
        return {"error": f"Connection failed: {e}"}


# ---------------------------
# Streamlit Layout
# ---------------------------
st.set_page_config(page_title="Orion Demo Suite", layout="wide")
st.title("🚀 Orion AI API Suite")

tab1, tab2 = st.tabs(["🧠 Memory", "✅ Task Tracker"])

# ---------------------------
# Tab 1: Memory
# ---------------------------
with tab1:
    st.header("🧠 Orion Memory")

    # Recall
    st.subheader("🔎 Recall Facts")
    if st.button("Recall"):
        resp = call_orion("recall")
        if isinstance(resp, list):
            if resp:
                st.write("### 🧾 Facts in memory:")
                for i, fact in enumerate(resp, 1):
                    st.write(f"💡 {i}. {fact}")
            else:
                st.info("No facts stored yet.")
        elif isinstance(resp, dict) and "error" in resp:
            st.error(resp["error"])
        else:
            st.write(resp)

    # Summarize
    st.subheader("📝 Summarize Memory")
    if st.button("Summarize Memory"):
        resp = call_orion("summarize")
        if resp and not isinstance(resp, dict):
            st.info(resp)
        else:
            st.warning("No summary available (API may not support summarize).")

    # Book Mode
    st.subheader("📚 Book Mode")
    book_text = st.text_area("Paste text or document to ingest into Orion Memory:")
    if st.button("Ingest Text"):
        if book_text.strip():
            chunks = textwrap.wrap(book_text, 1000)
            for chunk in chunks:
                call_orion("remember", {"content": chunk})
            st.success(f"📘 Ingested {len(chunks)} chunks into Orion Memory!")
        else:
            st.warning("⚠️ Nothing to ingest.")

    # Decay
    st.subheader("🌒 Decay")
    if st.button("Trigger Decay"):
        resp = call_orion("decay")
        st.write(resp if "error" not in resp else resp["error"])


# ---------------------------
# Tab 2: Task Tracker
# ---------------------------
with tab2:
    st.header("✅ Orion Task Tracker")

    conn = sqlite3.connect("orion_tasks.db", check_same_thread=False)
    c = conn.cursor()

    # Projects
    c.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        project_id TEXT PRIMARY KEY,
        name TEXT,
        created_at TIMESTAMP
    )
    """)

    # Tasks
    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        project_id TEXT,
        description TEXT,
        status TEXT,
        notes TEXT,
        due_date DATE,
        created_at TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(project_id)
    )
    """)
    conn.commit()

    # --- Create Project
    st.subheader("Start a Project")
    project_name = st.text_input("Enter project name:")
    if st.button("Create Project"):
        if project_name.strip():
            project_id = str(uuid.uuid4())[:8]
            c.execute("INSERT INTO projects (project_id, name, created_at) VALUES (?, ?, ?)",
                      (project_id, project_name, datetime.now()))
            conn.commit()
            call_orion("remember", {"content": f"Started new project: {project_name}"})
            st.success(f"✅ Project created: {project_name}")
            st.rerun()

    # --- Manage Projects
    st.subheader("Manage Projects & Tasks")
    c.execute("SELECT project_id, name FROM projects ORDER BY created_at DESC")
    projects = c.fetchall()

    if projects:
        selected_proj_id, selected_proj_name = st.selectbox(
            "Select a project:", options=projects, format_func=lambda p: p[1]
        )

        # Recall hints
        with st.expander("🧠 Memory suggestions"):
            hint = call_orion("recall")
            if isinstance(hint, list) and hint:
                for i, item in enumerate(hint, 1):
                    st.write(f"💡 {i}. {item}")
            elif isinstance(hint, dict) and "error" in hint:
                st.error(hint["error"])
            else:
                st.info("No suggestions.")

        # Delete Project
        if st.button(f"🗑️ Delete Project '{selected_proj_name}'"):
            c.execute("DELETE FROM tasks WHERE project_id=?", (selected_proj_id,))
            c.execute("DELETE FROM projects WHERE project_id=?", (selected_proj_id,))
            conn.commit()
            call_orion("remember", {"content": f"Deleted project: {selected_proj_name}"})
            st.warning(f"Project '{selected_proj_name}' deleted.")
            st.rerun()

        # --- Add Task
        st.write("### ➕ Add Task")
        task_desc = st.text_input("Task description:")
        task_status = st.selectbox("Status:", ["pending", "in_progress", "done"])
        task_notes = st.text_area("Notes (optional):")
        due_date = st.date_input("Due date (optional)", value=None)

        if st.button("Add Task"):
            if task_desc.strip():
                task_id = str(uuid.uuid4())[:8]
                c.execute("INSERT INTO tasks (task_id, project_id, description, status, notes, due_date, created_at) "
                          "VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (task_id, selected_proj_id, task_desc, task_status,
                           task_notes, due_date.isoformat() if isinstance(due_date, date) else None, datetime.now()))
                conn.commit()
                call_orion("remember", {"content": f"Task added to {selected_proj_name}: {task_desc}"})
                st.success("✅ Task added.")
                st.rerun()

        # --- Show Tasks
        st.write("### 📋 Task List")
        c.execute("SELECT description, status, notes, due_date FROM tasks WHERE project_id=?", (selected_proj_id,))
        rows = c.fetchall()

        if rows:
            df = pd.DataFrame(rows, columns=["Description", "Status", "Notes", "Due Date"])
            st.dataframe(df)

            # Chart
            st.write("### 📊 Status Overview")
            fig, ax = plt.subplots()
            df["Status"].value_counts().plot(kind="bar", ax=ax)
            st.pyplot(fig)

            # Export
            st.download_button("📥 Export CSV", df.to_csv(index=False), "tasks.csv", "text/csv")

            # AI Summary with fallback
            if st.button("🤖 Summarize Tasks"):
                # Try Orion API first
                summary = call_orion("summarize")
                if summary and not isinstance(summary, dict):
                    st.write("### 📝 AI Summary from Orion")
                    st.info(summary)
                else:
                    # Local fallback
                    summary_lines = []
                    for desc, status, notes, due in rows:
                        if due:
                            summary_lines.append(f"- {desc} (status: {status}, due {due})")
                        else:
                            summary_lines.append(f"- {desc} (status: {status})")

                    if summary_lines:
                        st.write("### 📝 Local Task Summary")
                        st.info("\n".join(summary_lines))
                    else:
                        st.warning("No tasks found to summarize.")
        else:
            st.info("No tasks yet. Add one above.")
    else:
        st.info("No projects yet. Create one above.")
