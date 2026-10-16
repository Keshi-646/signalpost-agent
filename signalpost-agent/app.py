"""Streamlit user interface for Signalpost Agent."""
import json
import streamlit as st
from signalpost.agent import CompanyAgent
from signalpost.collector import collect_profiles, export_profiles_json
from signalpost.database import history_for, profile_count, save_profile, list_profiles

st.set_page_config(page_title="Signalpost Agent", page_icon="🔎", layout="wide")
st.title("🔎 Signalpost — Company Information Agent")
st.caption("Verified company facts from Norway's official Central Coordinating Register for Legal Entities.")
st.info("Facts are retrieved from the official registry. Missing fields stay blank; this app does not invent facts or use an LLM to guess.")

with st.sidebar:
    st.header("Profile database")
    st.metric("Saved profiles", profile_count())
    target = st.number_input("Profiles to collect", min_value=1, max_value=1000, value=1000, step=100)
    if st.button("Collect company profiles", use_container_width=True):
        with st.spinner("Fetching real public registry records…"):
            result = collect_profiles(int(target))
        st.session_state["collection_result"] = result
        st.rerun()
    if st.button("Export profiles.json", use_container_width=True):
        count = export_profiles_json()
        st.success(f"Exported {count} profiles to profiles.json")
    if "collection_result" in st.session_state:
        st.json(st.session_state["collection_result"])

lookup_tab, database_tab, about_tab = st.tabs(["Company lookup", "Saved profiles", "How it works"])
with lookup_tab:
    st.subheader("Look up a Norwegian company")
    org_number = st.text_input("Organization number", placeholder="Enter 9 digits")
    if st.button("Find company", type="primary"):
        try:
            with st.spinner("Checking the official registry…"):
                profile = CompanyAgent().fetch(org_number)
                tracking = save_profile(profile)
            st.success("Company profile retrieved and saved.")
            left, right = st.columns([2, 1])
            with left:
                st.subheader(profile.get("name") or "Name not published")
                st.write(f"**Organization number:** {profile['org_number']}")
                st.write(f"**Status:** {profile['status']}")
                st.write(f"**Organization form:** {profile.get('organization_form') or 'Not available'}")
                st.write(f"**Industry:** {profile.get('industry') or 'Not available'}")
                st.write(f"**Address:** {profile.get('address') or 'Not available'}")
                st.write(f"**Website:** {profile.get('website') or 'Not available'}")
                st.write(f"**Employees:** {profile.get('employee_count') if profile.get('employee_count') is not None else 'Not available'}")
                st.write(f"**VAT registered:** {profile.get('vat_registered') if profile.get('vat_registered') is not None else 'Not available'}")
                st.write(f"**Founded:** {profile.get('founded_date') or 'Not available'}")
                st.write(f"**Latest accounts year:** {profile.get('latest_accounts_year') or 'Not available'}")
            with right:
                st.subheader("Evidence")
                st.markdown(f"[Open official source]({profile['source_url']})")
                st.caption(f"Retrieved at: {profile['retrieved_at']}")
                st.write(f"Fields with evidence: {len(profile['evidence'])}")
            st.subheader("Change tracking")
            if tracking["is_new"]:
                st.write("First saved observation. Future lookups will be compared with this snapshot.")
            elif tracking["changes"]:
                st.dataframe(tracking["changes"], use_container_width=True)
            else:
                st.write("No changes detected in tracked factual fields since the previous saved observation.")
            with st.expander("Full structured profile (JSON)"):
                st.code(json.dumps(profile, ensure_ascii=False, indent=2), language="json")
        except Exception as exc:
            st.error(str(exc))

with database_tab:
    st.subheader("Saved company profiles")
    profiles = list_profiles(500)
    if profiles:
        rows = [{"Organization number": p["org_number"], "Name": p.get("name"), "Status": p.get("status"), "Industry": p.get("industry"), "Retrieved at": p.get("retrieved_at")} for p in profiles]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("The table displays up to 500 saved profiles. Export the full database to JSON from the sidebar.")
    else:
        st.write("No profiles yet. Use the sidebar to collect profiles or look up a company.")
with about_tab:
    st.subheader("Design principles")
    st.markdown("""
    - **Identity first:** the returned organization number must match the requested number.
    - **Evidence:** every non-empty normalized fact points to the official registry record and retrieval timestamp.
    - **No fabrication:** unavailable fields remain null.
    - **Change history:** each lookup is stored as a snapshot; field-level differences are reported.
    - **Cost control:** official public registry API only; no paid LLM API is required.
    """)
    st.markdown("Official API: https://data.brreg.no/enhetsregisteret/api/dokumentasjon/en/index.html")
