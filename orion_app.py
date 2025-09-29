import streamlit as st
import sqlite3
import uuid
from datetime import datetime, date
import requests
import textwrap
import pandas as pd

st.set_page_config(page_title="Orion Demo Suite", page_icon="🛰️")

st.title("🛰️ Orion Demo Suite")
st.write("This app combines **Orion Memory** and an **AI-assisted Task Tracker** with persistence and exports.")

# ---------------------------
# Orion Memory API
# ---------------------------
ORION_API = "https://orion-memory.onrender.com"

"  # change if deployed

def call_orion(endpoint: str, payload=None, method="POST"):
    """Helper for Orion API calls."""
    try:
        if method == "POST":
            resp = requests.post(f"{ORION_API}/{endpoint}", json=payload or {})
        else:
            resp = requests.get(f"{ORION_API}/{endpoint}")
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        return {"error": str(e)}

def log_to_orion_memory(text: str):
    """Log a fact/event to Orion Memory."""
    resp = call_orion("remember", {"content": text})
    if "error" in resp:
        st.warning(f"⚠️ Memory log failed: {resp['error']}")

# ---------------------------
# Tabs
# ---------------------------
tab1, tab2 = st.tabs(["📖 Orion Memory", "✅ Task Tracker"])

# ---------------------------
# Tab 1: Orion Memory (Interactive)
# ---------------------------
with tab1:
    st.header("📖 Orion Memory")

    # Recall
    st.subheader("🔎 Recall")
    recall_query = st.text_input("What should Orion remember?", placeholder="Type here...")
    if st.button("Recall", key="recall_btn"):
        resp = call_orion("recall", {"query": recall_query})
        st.json(resp)

    # Summarize
    st.subheader("📝 Summarize")
    if st.button("Summarize Memory", key="summarize_btn"):
        resp = call_orion("summarize", method="GET")
        st.json(resp)

    # Book Mode with chunking
    st.subheader("📚 Book Mode (chunked ingest)")
    book_text = st.text_area("Paste a long doc/transcript/notes:")
    max_chunk = st.number_input("Max chars per chunk", min_value=400, max_value=4000, value=1000, step=100)
    if st.button("Ingest Text", key="book_mode_btn"):
        if book_text.strip():
            chunks = textwrap.wrap(book_text, max_chunk)
            ok = 0
            for i, chunk in enumerate(chunks, start=1):
                resp = call_orion("remember", {"content": chunk})
                if "error" in resp:
                    st.error(f"❌ Chunk {i}/{len(chunks)} failed: {resp['error']}")
                else:
                    ok += 1
                    st.success(f"📘 Ingested chunk {i}/{len(chunks)}")
            st.info(f"✅ Ingest complete: {ok}/{len(chunks)} chunks stored.")
        else:
            st.warning("⚠️ Paste some text first.")

    # Decay
    st.subheader("🌒 Decay")
    if st.button("Trigger Decay", key="decay_btn"):
        resp = call_orion("decay")
        st.json(resp)

# ---------------------------
# Tab 2: Orion Task Tracker (AI-enhanced)
# ---------------------------
with tab2:
    st.header("✅ Orion Task Tracker + AI")

    # --- Database Setup ---
    conn = sqlite3.connect("orion_tasks.db", check_same_thread=False)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        project_id TEXT PRIMARY KEY,
        name TEXT,
        created_at TIMESTAMP
    )
    """)

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

    # Ensure due_date exists
    c.execute("PRAGMA table_info(tasks)")
    cols = [r[1] for r in c.fetchall()]
    if "due_date" not in cols:
        try:
            c.execute("ALTER TABLE tasks ADD COLUMN due_date DATE")
            conn.commit()
        except Exception:
            pass

    # --- Start a Project ---
    st.subheader("Start a Project")
    project_name = st.text_input("Enter a new project name:")
    if st.button("Create Project"):
        if project_name.strip():
            project_id = str(uuid.uuid4())[:8]
            c.execute(
                "INSERT INTO projects (project_id, name, created_at) VALUES (?, ?, ?)",
                (project_id, project_name, datetime.now()),
            )
            conn.commit()
            st.success(f"✅ Project created: {project_name}")
            log_to_orion_memory(f"Started new project: {project_name}")
            st.rerun()
        else:
            st.error("⚠️ Please enter a valid project name.")

    # --- Manage Projects ---
    st.subheader("Manage Projects & Tasks")
    c.execute("SELECT project_id, name FROM projects ORDER BY created_at DESC")
    projects = c.fetchall()

    if projects:
        selected_proj_id, selected_proj_name = st.selectbox(
            "Select a project:",
            options=projects,
            format_func=lambda p: p[1],
        )

        # Memory-aware suggestion
        with st.expander("🧠 Memory suggestions for this project", expanded=False):
            hint = call_orion("recall", {"query": f"Any useful notes or reminders for project '{selected_proj_name}'?"})
            st.write(hint if "error" not in hint else "No suggestions or API unreachable.")

        # Delete project
        if st.button(f"🗑️ Delete Project '{selected_proj_name}' and all tasks"):
            c.execute("DELETE FROM tasks WHERE project_id=?", (selected_proj_id,))
            c.execute("DELETE FROM projects WHERE project_id=?", (selected_proj_id,))
            conn.commit()
            st.warning(f"Project '{selected_proj_name}' deleted.")
            log_to_orion_memory(f"Deleted entire project: {selected_proj_name}")
            st.rerun()

        # Add Task
        st.write("### ➕ Add Task")
        task_desc = st.text_input("Task description:", key="task_desc")
        task_status = st.selectbox("Task status:", ["pending", "in_progress", "done"], key="task_status")
        task_notes = st.text_area("Notes (optional):", key="task_notes")
        due_date = st.date_input("Due date (optional)", value=None)

        if st.button("Add Task"):
            if task_desc.strip():
                task_id = str(uuid.uuid4())[:8]
                c.execute(
                    "INSERT INTO tasks (task_id, project_id, description, status, notes, due_date, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (task_id, selected_proj_id, task_desc, task_status, task_notes,
                     due_date.isoformat() if isinstance(due_date, date) else None, datetime.now()),
                )
                conn.commit()
                st.success(f"✅ Task added: {task_desc}")
                log_to_orion_memory(f"Added task to project '{selected_proj_name}': {task_desc} (status: {task_status})")
                st.rerun()
            else:
                st.warning("⚠️ Please enter a task description.")

        # View tasks
        st.write("### 📋 Current Tasks")
        c.execute(
            "SELECT task_id, description, status, notes, due_date, created_at "
            "FROM tasks WHERE project_id=? ORDER BY created_at",
            (selected_proj_id,),
        )
        rows = c.fetchall()
        df = pd.DataFrame(rows, columns=["task_id", "description", "status", "notes", "due_date", "created_at"])

        # Insights
        if not df.empty:
            st.write("#### 📊 Insights")
            counts = df["status"].value_counts().reindex(["pending", "in_progress", "done"], fill_value=0)
            st.bar_chart(counts)

            today = date.today()
            overdue = df[(df["due_date"].notna()) & (df["status"] != "done")]
            overdue = overdue[overdue["due_date"].apply(lambda d: str(d) < today.isoformat())]
            if not overdue.empty:
                st.warning(f"⏰ Overdue tasks: {len(overdue)}")
        else:
            st.info("No tasks yet.")

        # Manage each task
        if not df.empty:
            for _, r in df.iterrows():
                tid = r["task_id"]
                desc = r["description"]
                status = r["status"]
                notes = r["notes"] or "—"
                due = r["due_date"]
                due_str = f", due {due}" if due else ""

                st.markdown(f"**{desc}** — *{status}* — _{notes}_ {due_str}")

                new_status = st.selectbox(
                    f"Update status for {desc}",
                    ["pending", "in_progress", "done"],
                    index=["pending", "in_progress", "done"].index(status),
                    key=f"status_{tid}"
                )
                if new_status != status:
                    c.execute("UPDATE tasks SET status=? WHERE task_id=?", (new_status, tid))
                    conn.commit()
                    st.info(f"🔄 Updated '{desc}' → {new_status}")
                    log_to_orion_memory(f"Task '{desc}' updated to {new_status}")
                    st.rerun()

                new_due = st.date_input(f"Due date for {desc}", value=None, key=f"due_{tid}")
                if new_due:
                    c.execute("UPDATE tasks SET due_date=? WHERE task_id=?", (new_due.isoformat(), tid))
                    conn.commit()
                    st.info(f"🗓️ Updated '{desc}' due date to {new_due}")
                    st.rerun()

                if st.button(f"❌ Delete '{desc}'", key=f"delete_{tid}"):
                    c.execute("DELETE FROM tasks WHERE task_id=?", (tid,))
                    conn.commit()
                    st.warning(f"🗑️ Task '{desc}' deleted.")
                    log_to_orion_memory(f"Deleted task '{desc}'")
                    st.rerun()

        # Export
        if not df.empty:
            csv = df.drop(columns=["task_id"]).to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv, file_name=f"{selected_proj_name}_tasks.csv", mime="text/csv")

            md = "\n".join([f"- **{row['description']}** — {row['status']} — due: {row['due_date'] or '-'}"
                            for _, row in df.iterrows()])
            st.download_button("⬇️ Download Markdown", md.encode("utf-8"),
                               file_name=f"{selected_proj_name}_tasks.md", mime="text/markdown")

        # AI Summary
        if st.button("🧠 Summarize Project (AI)"):
            if not df.empty:
                task_text = "\n".join([f"{row['description']} [{row['status']}] (due: {row['due_date'] or '-'})"
                                       for _, row in df.iterrows()])
                resp = call_orion("recall", {"query": f"Summarize project '{selected_proj_name}':\n{task_text}"})
                st.info(resp)
            else:
                st.warning("⚠️ No tasks to summarize.")
    else:
        st.info("No projects yet. Create one above first.")
