import streamlit as st
import requests

# Orion Memory API endpoint
ORION_API = "https://orion-memory.onrender.com"
USER_ID = "demo"

st.set_page_config(page_title="Orion Demo Suite", layout="wide")

st.title("🧠 Orion Demo Suite")

tabs = st.tabs(["Memory", "Task Manager"])

# ============================================================
# MEMORY TAB
# ============================================================
with tabs[0]:
    st.header("Orion Memory")

    # ----------------- Add Fact -----------------
    st.subheader("➕ Add a Fact")
    new_fact = st.text_area("Enter something for Orion to remember", key="new_fact")
    if st.button("Save Fact"):
        if new_fact.strip():
            resp = requests.post(f"{ORION_API}/fact", json={"user_id": USER_ID, "fact": new_fact})
            if resp.status_code == 200:
                st.success("✅ Orion remembered it.")
            else:
                st.error("❌ Failed to save fact.")
        else:
            st.warning("Please enter something first.")

    st.divider()

    # ----------------- Book Mode -----------------
    st.subheader("📚 Book Mode")
    big_input = st.text_area("Paste large text (e.g., book chapter, long notes)", key="book_mode")
    if st.button("Summarize Book Mode"):
        if big_input.strip():
            resp = requests.post(f"{ORION_API}/fact", json={"user_id": USER_ID, "fact": f"BookMode: {big_input}"})
            if resp.status_code == 200:
                st.success("Text ingested. Orion will attempt layered summarization.")
            else:
                st.error("❌ Failed to process Book Mode input.")

    st.divider()

    # ----------------- Recall -----------------
    st.subheader("🔍 Recall")
    query = st.text_input("What should Orion recall?", key="recall_query")

    if st.button("Run Recall"):
        if query.strip():
            resp = requests.get(f"{ORION_API}/recall/{USER_ID}", params={"query": query})
            if resp.status_code == 200:
                results = resp.json()
                st.session_state.last_results = results
                if not results:
                    st.info("I couldn’t find anything for that query.")
                else:
                    st.write("### Results")
                    for f in results:
                        st.write(f"- {f}")
            else:
                st.error("❌ API error.")
        else:
            st.warning("Please enter a query first.")

    # ----------------- Feedback -----------------
    if "last_results" in st.session_state and st.session_state.last_results:
        st.divider()
        st.subheader("Feedback on Recall")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("👍 Looks good"):
                requests.post(f"{ORION_API}/fact", json={
                    "user_id": USER_ID,
                    "fact": "Feedback: approved output"
                })
                st.success("Thanks for the feedback!")

        with col2:
            if st.button("👎 Needs correction"):
                st.session_state.show_correction = True

        if st.session_state.get("show_correction", False):
            with st.form("correction_form", clear_on_submit=True):
                correction = st.text_area("Enter correction:", key="correction_text")
                save = st.form_submit_button("Save Correction")
                if save:
                    if correction.strip():
                        requests.post(f"{ORION_API}/fact", json={
                            "user_id": USER_ID,
                            "fact": f"Correction: {correction.strip()}"
                        })
                        st.success("Correction saved. Orion will remember it.")
                        st.session_state.show_correction = False
                    else:
                        st.warning("Please enter a correction before saving.")

    st.divider()

    # ----------------- Clear Memory -----------------
    if st.button("🧹 Clear All Memory"):
        resp = requests.post(f"{ORION_API}/clear/{USER_ID}")
        if resp.status_code == 200:
            st.success("Memory cleared.")
            st.session_state.pop("last_results", None)
            st.session_state.show_correction = False
        else:
            st.error("Failed to clear memory.")

# ============================================================
# TASK MANAGER TAB
# ============================================================
with tabs[1]:
    st.header("Orion Task Manager")

    if "projects" not in st.session_state:
        st.session_state.projects = {}

    project_name = st.text_input("Project Name", key="proj_name")
    if st.button("➕ Add Project"):
        if project_name.strip() and project_name not in st.session_state.projects:
            st.session_state.projects[project_name] = []
            st.success(f"Project {project_name} created.")

    if st.session_state.projects:
        selected_proj = st.selectbox("Select Project", list(st.session_state.projects.keys()))
        task = st.text_input("Task Description", key="task_desc")
        if st.button("➕ Add Task"):
            if task.strip():
                st.session_state.projects[selected_proj].append(task)
                st.success(f"Task added to {selected_proj}.")

        if st.button("📋 Summarize Tasks"):
            tasks = st.session_state.projects[selected_proj]
            if tasks:
                summary = f"Project {selected_proj} has {len(tasks)} tasks: " + "; ".join(tasks)
                st.info(summary)
            else:
                st.info("No tasks yet.")
