import streamlit as st
import requests
import pandas as pd

ORION_API = "https://orion-memory.onrender.com"
USER_ID = "demo"

st.set_page_config(page_title="Orion Demo Suite", layout="wide")

st.title("🧠 Orion Demo Suite")

tabs = st.tabs(["Memory", "Task Manager"])

# ----------------------------
# MEMORY TAB
# ----------------------------
with tabs[0]:
    st.header("Orion Memory")

    # Fact entry
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

    # Recall
    st.subheader("🔍 Recall")
    query = st.text_input("What should Orion recall?", key="recall_query")
    if st.button("Run Recall"):
        if query.strip():
            resp = requests.get(f"{ORION_API}/recall/{USER_ID}", params={"query": query})
            if resp.status_code == 200:
                facts = resp.json()
                if not facts:
                    st.info("I couldn’t find anything for that query.")
                else:
                    st.write("### Results")
                    for f in facts:
                        st.write(f"- {f}")
                    
                    # ------------------------
                    # Feedback (fixed)
                    # ------------------------
                    with st.expander("Feedback"):
                        if "correction_mode" not in st.session_state:
                            st.session_state.correction_mode = False

                        col1, col2 = st.columns([1,1])
                        with col1:
                            if st.button("👍 Looks good"):
                                requests.post(f"{ORION_API}/fact", json={
                                    "user_id": USER_ID,
                                    "fact": "Feedback: approved output"
                                })
                                st.success("Thanks for the feedback!")

                        with col2:
                            if st.button("👎 Needs correction"):
                                st.session_state.correction_mode = True

                        if st.session_state.correction_mode:
                            with st.form("correction_form", clear_on_submit=True):
                                correction = st.text_input("Enter the correct fact:")
                                save = st.form_submit_button("Save Correction")
                                if save:
                                    if correction.strip():
                                        requests.post(f"{ORION_API}/fact", json={
                                            "user_id": USER_ID,
                                            "fact": f"Correction: {correction.strip()}"
                                        })
                                        st.success("Correction saved.")
                                        st.session_state.correction_mode = False
                                    else:
                                        st.warning("Enter something before saving.")
        else:
            st.warning("Please enter a query first.")

    st.divider()

    # Clear memory
    if st.button("🧹 Clear All Memory"):
        resp = requests.post(f"{ORION_API}/clear/{USER_ID}")
        if resp.status_code == 200:
            st.success("Memory cleared.")
        else:
            st.error("Failed to clear memory.")

# ----------------------------
# TASK MANAGER TAB
# ----------------------------
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
