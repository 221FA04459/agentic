import os
import io
import base64
import requests
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# -----------------------------
# Streamlit Page Config
# -----------------------------
st.set_page_config(page_title="Agentic AI Compliance Officer", layout="wide")

st.title("Agentic AI Compliance Officer")
st.caption("LangChain + Gemini • FastAPI • Streamlit")

# -----------------------------
# Sidebar Settings
# -----------------------------
with st.sidebar:
    st.header("Settings")
    api_base = st.text_input("API Base URL", API_BASE)
    st.write("Use the tabs to upload documents, check compliance, and generate reports.")

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Upload Regulation", "Compliance Check", "Reports", "Monitoring"])

# -----------------------------
# Tab 1: Upload Regulation
# -----------------------------
with tab1:
    st.subheader("Upload Regulation Document")
    uploaded = st.file_uploader("Choose a file (PDF/DOC/DOCX/TXT)", type=["pdf", "doc", "docx", "txt"])
    col1, col2, col3 = st.columns(3)
    with col1:
        reg_type = st.text_input("Regulation Type", "gdpr")
    with col2:
        jurisdiction = st.text_input("Jurisdiction", "EU")
    with col3:
        effective_date = st.text_input("Effective Date (YYYY-MM-DD)", "")

    if st.button("Upload & Analyze", type="primary"):
        if not uploaded:
            st.warning("Please upload a file.")
        else:
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            data = {"regulation_type": reg_type, "jurisdiction": jurisdiction, "effective_date": effective_date}
            with st.spinner("Uploading and processing..."):
                r = requests.post(f"{api_base}/upload_regulation", files=files, data=data, timeout=600)
            if r.ok:
                res = r.json()
                st.success("Uploaded. Background processing started.")
                st.json(res)
            else:
                st.error(r.text)

    st.divider()
    st.subheader("Existing Regulations")
    if st.button("Refresh Regulations"):
        try:
            with st.spinner("Contacting API (may take up to 2 minutes on cold start)..."):
                r = requests.get(f"{api_base}/regulations", timeout=180)
            if r.ok:
                data = r.json().get("data", {})
                items = data.get("items", [])
                st.write(f"Found {len(items)} item(s)")
                st.json(items)
            else:
                st.error(r.text)
        except requests.exceptions.ReadTimeout:
            st.error("Timed out waiting for the API. If this is the first request after a while, the service may be cold starting. Please try again in a few seconds.")

# -----------------------------
# Tab 2: Compliance Check
# -----------------------------
with tab2:
    st.subheader("Run Compliance Check")
    reg_id = st.text_input("Regulation ID")
    st.caption("Provide key company policies below (one per line or paragraph).")
    policies_text = st.text_area("Company Policies", height=200)

    if st.button("Check Compliance", type="primary"):
        if not reg_id:
            st.warning("Enter a regulation ID")
        else:
            payload = {
                "regulation_id": reg_id,
                "company_policies": [p.strip() for p in policies_text.split("\n") if p.strip()]
            }
            with st.spinner("Assessing compliance..."):
                r = requests.post(f"{api_base}/check_compliance", json=payload, timeout=600)
            if r.ok:
                res = r.json().get("data", {})
                st.success("Compliance check complete")

                # -----------------------------
                # Display Summary
                # -----------------------------
                st.metric("Compliance Score", res.get("compliance_score", 0))
                st.write("Overall Status:", res.get("overall_status"))

                # -----------------------------
                # Compliance Table
                # -----------------------------
                gaps = res.get("gaps", [])
                if gaps:
                    df_gaps = pd.DataFrame(gaps)
                    st.subheader("Compliance Details")
                    st.dataframe(df_gaps)

                    # Pie chart
                    st.subheader("Compliance Distribution")
                    counts = df_gaps['status'].value_counts()
                    fig, ax = plt.subplots()
                    ax.pie(
                        counts,
                        labels=counts.index,
                        autopct="%1.1f%%",
                        startangle=90,
                        colors=['#4CAF50', '#FFC107', '#F44336']
                    )
                    ax.axis('equal')
                    st.pyplot(fig)
                else:
                    st.info("No gaps detected. Fully compliant!")

                # Recommendations
                recs = res.get("recommendations", [])
                if recs:
                    st.subheader("Recommendations")
                    for i, r in enumerate(recs, 1):
                        st.write(f"{i}. {r}")
            else:
                st.error(r.text)

# -----------------------------
# Tab 3: Generate & Download Reports
# -----------------------------
with tab3:
    st.subheader("Generate & Download Professional Reports")
    reg_id_r = st.text_input("Regulation ID for Report")
    include_recs = st.checkbox("Include Recommendations", True)

    if st.button("Generate & Preview PDF", type="primary"):
        if not reg_id_r:
            st.warning("Enter a regulation ID")
        else:
            payload = {"regulation_id": reg_id_r, "include_recommendations": include_recs}
            with st.spinner("Generating professional PDF..."):
                resp = requests.post(f"{api_base}/generate_professional_report", json=payload, timeout=600)

            if resp.ok:
                pdf_bytes = resp.content
                if not pdf_bytes:
                    st.error("Empty PDF returned from backend")
                else:
                    # Download button
                    st.download_button(
                        "Download PDF",
                        data=pdf_bytes,
                        file_name=f"compliance_report_{reg_id_r}.pdf",
                        mime="application/pdf",
                    )
                    # Inline preview
                    b64 = base64.b64encode(pdf_bytes).decode()
                    st.markdown(
                        f"<iframe src='data:application/pdf;base64,{b64}' width='100%' height='800px'></iframe>",
                        unsafe_allow_html=True,
                    )
                    st.success("PDF ready!")
            else:
                st.error(resp.text)

# -----------------------------
# Tab 4: Monitoring
# -----------------------------
with tab4:
    st.subheader("Regulatory Monitoring")
    st.caption("Add sources to monitor, run checks, and view detected changes.")

    with st.expander("Add Source"):
        m_name = st.text_input("Name", "GDPR EUR-Lex", key="m_name")
        m_url = st.text_input("URL", "https://eur-lex.europa.eu/eli/reg/2016/679/oj", key="m_url")
        m_jur = st.text_input("Jurisdiction", "EU", key="m_jur")
        m_type = st.text_input("Regulation Type", "gdpr", key="m_type")
        m_due = st.number_input("Due in (days) — optional", min_value=0, value=0, step=1, key="m_due")
        if st.button("Add Source", key="m_add"):
            params = {
                "name": m_name,
                "url": m_url,
                "jurisdiction": m_jur,
                "regulation_type": m_type,
            }
            if m_due > 0:
                params["due_days"] = m_due
            r = requests.post(f"{api_base}/monitor/sources", params=params, timeout=60)
            if r.ok:
                st.success("Source added")
            else:
                st.error(r.text)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Refresh Sources", key="m_list"):
            try:
                r = requests.get(f"{api_base}/monitor/sources", timeout=180)
                if r.ok:
                    data = r.json().get("data", {})
                    items = data.get("items", [])
                    st.write(f"{len(items)} source(s)")
                    st.json(items)
                else:
                    st.error(r.text)
            except requests.exceptions.ReadTimeout:
                st.error("Timed out waiting for sources. Please retry; the API may be cold starting.")
    with col_b:
        if st.button("Run Monitor Now", key="m_run"):
            try:
                r = requests.post(f"{api_base}/monitor/run", timeout=300)
                if r.ok:
                    st.success(r.json())
                else:
                    st.error(r.text)
            except requests.exceptions.ReadTimeout:
                st.error("Timed out running monitor. Try again in a moment.")
