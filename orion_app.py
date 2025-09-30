import streamlit as st
import requests
import pandas as pd

# ✅ Make sure this URL points to your live Orion Memory API:
ORION_API = "https://orion-memory.onrender.com"
user_id = "demo"

st.set_page_config(page_title="🧠 Orion Demo Suite", layout="wide")
st.title("🧠 Orion Demo Suite")

tabs = st.tabs(["Memory", "Task Manager", "Provenance"])

# --- MEMORY TAB ---
with tabs[0]:
    st.header("📚 Orion Memory")
    st.write("Add facts, recall them, or paste large text into Book Mode.")

    # Single fact
    fact_input = st.text_input("Enter a fact to remember", key="fact_input")
    if st.button("Remember Fact"):
        if fact_input.strip():
            resp = requests.post(
                f"{ORION_API}/fact",
                json={"user_id": user_id, "fact": fact_input}
            )
            if resp.status_code == 200:
                st.success("Fact remembered.")
            else:
                st.error(resp.text)

    # Recall with fallback summary
    query = st.text_input("Recall something (query)", key="recall_input")
    if st.button("Recall"):
        resp = requests.get(f"{ORION_API}/recall/{user_id}", params={"query": query})
        if resp.status_code == 200:
            results = resp.json()
            if results:
                st.subheader("🔎 Recall Results")
                for r in results:
                    st.write("-", r)
            else:
                # fallback: get all facts
                all_facts = requests.get(f"{ORION_API}/recall/{user_id}").json()
                if all_facts:
                    st.info("No match found. Showing all facts instead:")
                    for r in all_facts:
                        st.write("-", r)
                else:
                    st.warning("No facts saved yet.")
        else:
            st.error(resp.text)

    # Book Mode
    st.subheader("📚 Book Mode")
    book_input = st.text_area("Paste long text here for Book Mode", height=150, key="book_input")
    if st.button("Submit to Book Mode"):
        if book_input.strip():
            resp = requests.post(
                f"{ORION_API}/fact/bookmode/{user_id}",
                json={"fact": book_input}
            )
            if resp.status_code == 200:
                st.success("Book Mode content saved.")
            else:
                st.error(resp.text)

# --- TASK MANAGER TAB ---
with tabs[1]:
    st.header("✅ Orion Task Manager")
    st.write("Create projects and tasks with AI assistance.")

    if "projects" not in st.session_state:
        st.session_state.projects = {}

    new_project = st.text_input("New project name", key="new_project")
    if st.button("Add Project"):
        if new_project.strip():
            st.session_state.projects[new_project] = []
            st.success(f"Project '{new_project}' added.")

    if st.session_state.projects:
        project = st.selectbox("Select project", list(st.session_state.projects.keys()))
        task_desc = st.text_input("New task", key="task_desc")
        if st.button("Add Task"):
            if task_desc.strip():
                st.session_state.projects[project].append({"task": task_desc, "done": False})
                st.success("Task added.")

        if st.session_state.projects[project]:
            df = pd.DataFrame(st.session_state.projects[project])
            st.table(df)
        else:
            st.info("No tasks yet for this project.")
    else:
        st.info("No projects yet. Add one above.")

# --- PROVENANCE TAB ---
with tabs[2]:
    st.header("🔍 Provenance Viewer")
    st.write("See all facts with their source and timestamp.")

    if st.button("Load Provenance"):
        resp = requests.get(f"{ORION_API}/provenance/{user_id}")
        if resp.status_code == 200:
            provenance = resp.json()
            if provenance:
                for i, entry in enumerate(provenance, 1):
                    st.markdown(
                        f"**{i}. [{entry['timestamp']}] ({entry['source']})** — {entry['fact']}"
                    )
            else:
                st.info("No provenance records yet.")
        else:
            st.error(resp.text)

    if st.button("Clear Memory"):
        resp = requests.post(f"{ORION_API}/clear/{user_id}")
        if resp.status_code == 200:
            st.success("Memory cleared.")
        else:
            st.error(resp.text)
