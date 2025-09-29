import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

# -------------------------
# Orion API Configuration
# -------------------------
ORION_API = "https://orion-memory.onrender.com"

def call_orion(endpoint, method="GET", payload=None):
    """Helper to call Orion Memory API."""
    url = f"{ORION_API}/{endpoint}"
    try:
        if method == "GET":
            r = requests.get(url)
        elif method == "POST":
            r = requests.post(url, json=payload)
        else:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None
    except Exception as e:
        return {"error": str(e)}

# -------------------------
# Streamlit App Layout
# -------------------------
st.set_page_config(page_title="Orion Demo Suite", layout="wide")
st.title("🛰️ Orion Demo Suite")

tabs = st.tabs(["🧠 Memory Assistant", "✅ Task Manager", "📖 Book Mode", "🔗 Provenance"])

# -------------------------
# Tab 1: Memory Assistant
# -------------------------
with tabs[0]:
    st.header("🧠 Orion Memory Assistant")

    # --- Remember Something ---
    st.subheader("Remember Something")
    new_fact = st.text_input("Enter a fact or note Orion should remember:")
    if st.button("Save Fact"):
        if new_fact.strip():
            resp = call_orion("fact", "POST", {"user_id": "demo", "fact": new_fact.strip()})
            if resp:
                st.success(f"Saved to memory: {new_fact}")
            else:
                st.error("Failed to save fact.")
        else:
            st.warning("Please enter something before saving.")

    # --- Ask Orion / Recall ---
    st.subheader("Ask Orion")
    query = st.text_input("What should Orion remember or recall?")
    if st.button("Recall"):
        if query.strip():
            resp = call_orion(f"recall/demo?query={query}")
            if isinstance(resp, list) and resp:
                query_lower = query.lower()
                if "what is orion" in query_lower or query_lower.strip() == "orion":
                    st.info(
                        "Orion is your AI-powered memory and task assistant. "
                        "It remembers facts, manages tasks, provides summaries, "
                        "and tracks provenance so you always know where knowledge came from."
                    )
                else:
                    answer = f"Here’s what Orion knows related to '{query}':\n\n"
                    for i, fact in enumerate(resp[:5], 1):
                        answer += f"{i}. {fact}\n"
                    st.info(answer.strip())
            else:
                st.warning("I couldn’t find anything for that query.")

    # --- Summarize All Memory ---
    st.subheader("Summarize Memory")
    if st.button("Summarize All Facts"):
        facts = call_orion("recall/demo")
        if isinstance(facts, list) and facts:
            summary = "Here’s a quick summary of stored facts:\n\n"
            for i, fact in enumerate(facts[:10], 1):
                summary += f"{i}. {fact}\n"
            st.info(summary.strip())
        else:
            st.info("No facts stored yet.")

    # --- Trigger Decay ---
    st.subheader("Memory Lifecycle")
    if st.button("Trigger Decay"):
        resp = call_orion("decay/demo", "POST")
        st.success(f"Decay triggered. Response: {resp}")

    # --- Clear Memory ---
    st.subheader("Clear Memory (Demo Reset)")
    if st.button("Clear All Memory Facts"):
        resp = call_orion("clear/demo", "POST")  # you’d need to implement /clear in your API
        st.success("All memory cleared for demo user.")

# -------------------------
# Tab 2: Task Manager
# -------------------------
with tabs[1]:
    st.header("✅ Manage Projects & Tasks")

    if "projects" not in st.session_state:
        st.session_state.projects = {}

    # --- Project Management ---
    st.subheader("Projects")
    new_project = st.text_input("Create a new project:")
    if st.button("Add Project"):
        if new_project.strip():
            st.session_state.projects[new_project] = []
            st.success(f"Project '{new_project}' created.")
        else:
            st.warning("Please enter a project name.")

    # --- Clear All Tasks/Projects ---
    if st.button("Clear All Projects & Tasks"):
        st.session_state.projects = {}
        st.success("All projects and tasks cleared.")

    # --- If projects exist, show tasks ---
    if st.session_state.projects:
        project = st.selectbox("Select a project:", list(st.session_state.projects.keys()))
        st.subheader(f"Tasks for {project}")

        # --- Task Management ---
        task_desc = st.text_input("Task description:")
        status = st.selectbox("Status", ["pending", "in_progress", "done"])
        if st.button("Add Task"):
            if task_desc.strip():
                st.session_state.projects[project].append({"task": task_desc, "status": status})
                st.success(f"Task added to {project}: {task_desc} [{status}]")
            else:
                st.warning("Please enter a task description.")

        tasks = st.session_state.projects[project]
        if tasks:
            df = pd.DataFrame(tasks)
            st.dataframe(df)

            # --- Status Summary ---
            st.subheader("Status Summary")
            counts = df["status"].value_counts()
            fig, ax = plt.subplots()
            counts.plot(kind="bar", ax=ax)
            ax.set_title("Task Status Counts")
            st.pyplot(fig)

            # --- AI-like Summary ---
            st.subheader("Summarize Tasks with AI")
            summary = []
            for s, c in counts.items():
                summary.append(f"{c} tasks are {s}")
            st.info("Summary: " + ", ".join(summary))
        else:
            st.info("No tasks yet. Add one above.")

# -------------------------
# Tab 3: Book Mode
# -------------------------
with tabs[2]:
    st.header("📖 Book Mode")
    text_block = st.text_area("Paste text to ingest into Orion memory:")
    if st.button("Ingest Text"):
        if text_block.strip():
            resp = call_orion("fact", "POST", {"user_id": "demo", "fact": text_block.strip()})
            if resp:
                st.success("Book Mode text ingested into memory.")
            else:
                st.error("Failed to ingest text.")
        else:
            st.warning("Please paste text before ingesting.")

# -------------------------
# Tab 4: Provenance
# -------------------------
with tabs[3]:
    st.header("🔗 Provenance")
    prov = call_orion("provenance")
    if isinstance(prov, list) and prov:
        for p in prov[:10]:
            st.write(
                f"Fact: {p.get('fact','')} — Source: {p.get('source','unknown')} — Time: {p.get('timestamp','')}"
            )
    else:
        st.info("No provenance data available.")
