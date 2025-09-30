import streamlit as st
import pandas as pd
import sqlite3
import re
from datetime import datetime

# ================================================================
# Storage (SQLite) — sticky memory for demo
# ================================================================
DB_PATH = "orion_memories.db"

def db_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with db_conn() as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS facts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                fact TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                ts TEXT DEFAULT (datetime('now'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prefs(
                user_id TEXT PRIMARY KEY,
                answer_style TEXT CHECK(answer_style IN ('short','detailed')) NOT NULL DEFAULT 'short',
                ts TEXT DEFAULT (datetime('now'))
            )
        """)
        con.commit()

def save_pref(user_id: str, style: str):
    with db_conn() as con:
        cur = con.cursor()
        cur.execute("""
            INSERT INTO prefs(user_id, answer_style, ts)
            VALUES(?,?,datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                answer_style=excluded.answer_style,
                ts=datetime('now')
        """, (user_id, style))
        con.commit()

def get_pref(user_id: str) -> str:
    with db_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT answer_style FROM prefs WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row[0] if row else "short"

def add_fact(user_id: str, fact: str, source: str = "manual"):
    fact = fact.strip()
    if not fact:
        return
    with db_conn() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO facts(user_id, fact, source, ts) VALUES(?,?,?,datetime('now'))",
            (user_id, fact, source)
        )
        con.commit()

def clear_facts(user_id: str):
    with db_conn() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM facts WHERE user_id=?", (user_id,))
        con.commit()

def get_facts(user_id: str):
    with db_conn() as con:
        cur = con.cursor()
        cur.execute("""
            SELECT id, fact, source, ts
            FROM facts
            WHERE user_id=?
            ORDER BY id DESC
        """, (user_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "fact": r[1], "source": r[2], "timestamp": r[3]} for r in rows]

# ================================================================
# Text helpers
# ================================================================
def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]

def first_sentence(text: str) -> str:
    parts = split_sentences(text)
    return parts[0] if parts else text

def style_answer(text: str, style: str) -> str:
    if style == "short":
        s = first_sentence(text)
        words = s.split()
        return " ".join(words[:20]) + ("…" if len(words) > 20 else "")
    return text

# ================================================================
# Streamlit App
# ================================================================
st.set_page_config(page_title="Orion AI Demo Suite", layout="wide")
st.title("🧠 Orion AI Demo Suite")

init_db()

USER_ID = "demo"

page = st.sidebar.radio("Navigate", ["Preferences", "Orion Memory", "Task Manager"])

# -------------------------------
# Preferences
# -------------------------------
if page == "Preferences":
    st.header("⚙️ Preferences")
    current = get_pref(USER_ID)
    choice = st.radio("Answer style", ["short", "detailed"], index=0 if current == "short" else 1, horizontal=True)
    if st.button("Save Preferences"):
        save_pref(USER_ID, choice)
        st.success(f"Saved — Orion will answer in **{choice}** style.")

    facts_count = len(get_facts(USER_ID))
    st.caption(f"Memory size: {facts_count} facts.")

# -------------------------------
# Orion Memory
# -------------------------------
elif page == "Orion Memory":
    st.header("📚 Orion Memory")

    st.subheader("Quick Fact")
    fact = st.text_input("Enter a single fact for Orion to remember")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Fact"):
            if fact.strip():
                add_fact(USER_ID, fact.strip(), source="manual")
                st.success("Fact saved.")
            else:
                st.warning("Please enter something first.")
    with col2:
        if st.button("Clear Memory"):
            clear_facts(USER_ID)
            st.success("All memory cleared for demo user.")

    st.divider()

    st.subheader("Book Mode (Paste multiple sentences)")
    text = st.text_area("Paste text for Orion to remember (it splits into sentences and adds a summary)", height=180)
    if st.button("Remember (Book Mode)"):
        if text.strip():
            sentences = split_sentences(text)
            stored = 0
            for s in sentences:
                add_fact(USER_ID, s, source="book_mode")
                stored += 1
            summary = " ".join(sentences[:2]) if len(sentences) > 1 else sentences[0]
            add_fact(USER_ID, f"Summary: {summary}", source="book_mode_summary")
            st.success(f"Stored {stored} facts + 1 summary from Book Mode.")
        else:
            st.warning("Please paste some text.")

    st.divider()

    st.subheader("🔍 Recall")
    query = st.text_input("Ask Orion (e.g., What is Orion?)")
    if st.button("Recall"):
        style = get_pref(USER_ID)
        facts = get_facts(USER_ID)

        if not facts:
            st.info("No memory found yet.")
        else:
            hits = []
            if query:
                for f in facts:
                    if query.lower() in f["fact"].lower():
                        hits.append(f)
            if not hits and query:
                qwords = [w for w in query.lower().split() if len(w) > 2]
                for f in facts:
                    if any(w in f["fact"].lower() for w in qwords):
                        hits.append(f)
            results = hits if hits else facts[:5]

            st.write(f"**Answer style:** `{style}`")
            for f in results:
                rendered = style_answer(f["fact"], style)
                st.markdown(f"- **{rendered}**  _(source: {f['source']}, time: {f['timestamp'][:19]})_")

            # ✅ Fixed Feedback UI
            with st.expander("Feedback"):
                if "show_correction" not in st.session_state:
                    st.session_state["show_correction"] = False

                fb_col1, fb_col2 = st.columns([1, 2])
                with fb_col1:
                    if st.button("👍 Looks good"):
                        add_fact(USER_ID, "Feedback: user approved the recall output.", source="feedback_up")
                        st.success("Thanks! Orion recorded your positive feedback.")
                with fb_col2:
                    if st.button("👎 Needs correction"):
                        st.session_state["show_correction"] = True

                if st.session_state["show_correction"]:
                    correction = st.text_input("What should Orion remember instead?", key="correction_input")
                    if st.button("Save Correction"):
                        if correction.strip():
                            add_fact(USER_ID, f"Correction: {correction.strip()}", source="feedback_down")
                            st.success("Saved correction — Orion will keep this in mind.")
                            st.session_state["show_correction"] = False
                        else:
                            st.warning("Please enter a correction before saving.")

    if st.button("Summarize Facts"):
        facts = get_facts(USER_ID)
        if facts:
            texts = [f["fact"] for f in facts]
            highlights = ", ".join([first_sentence(t) for t in texts[:3]]) + ("…" if len(texts) > 3 else "")
            st.success(f"Orion currently remembers {len(facts)} facts. Highlights: {highlights}")
        else:
            st.info("No facts to summarize yet.")

# -------------------------------
# Task Manager (unchanged)
# -------------------------------
elif page == "Task Manager":
    st.header("✅ Orion Task Manager")

    if "projects" not in st.session_state:
        st.session_state["projects"] = {}
        st.session_state["active_project"] = None

    new_proj = st.text_input("New Project Name")
    if st.button("Create Project"):
        if new_proj:
            st.session_state["projects"][new_proj] = []
            st.session_state["active_project"] = new_proj
            st.success(f"Project created: {new_proj}")

    if st.session_state["projects"]:
        project = st.selectbox(
            "Select Project",
            options=list(st.session_state["projects"].keys()),
            index=list(st.session_state["projects"].keys()).index(st.session_state["active_project"]) if st.session_state["active_project"] else 0
        )
        st.session_state["active_project"] = project

        task_desc = st.text_input("Task Description")
        if st.button("Add Task"):
            if task_desc:
                st.session_state["projects"][project].append(
                    {"task": task_desc, "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                )
                st.success(f"Task added to {project}")

        tasks = st.session_state["projects"][project]
        if tasks:
            df = pd.DataFrame(tasks)
            st.table(df)
        else:
            st.info("No tasks yet.")

        if st.button("Summarize Tasks"):
            task_texts = [t["task"] for t in tasks]
            if task_texts:
                summary = (
                    f"This project has {len(task_texts)} tasks. "
                    f"Focus: {', '.join(task_texts[:3])}" + ("..." if len(task_texts) > 3 else "")
                )
                st.success(summary)
            else:
                st.info("No tasks to summarize.")

        if st.button("Clear Tasks"):
            st.session_state["projects"][project] = []
            st.success(f"Cleared tasks for {project}")
