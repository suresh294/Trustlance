import streamlit as st
import requests
import time
import pandas as pd
import plotly.express as px
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Trustlance",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

    .main {
        background-color: #f7f8fc;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }

    .hero {
        background: linear-gradient(135deg, #111827, #1e3a8a);
        padding: 35px;
        border-radius: 18px;
        color: white;
        margin-bottom: 25px;
    }

    .hero h1 {
        font-size: 42px;
        margin-bottom: 5px;
    }

    .hero p {
        font-size: 18px;
        opacity: 0.9;
    }

    .card {
        background: white;
        padding: 22px;
        border-radius: 15px;
        border: 1px solid #e5e7eb;
        margin-bottom: 15px;
    }

    .job-card {
        background: white;
        padding: 22px;
        border-radius: 15px;
        border: 1px solid #e5e7eb;
        margin-bottom: 18px;
    }

    .status-created {
        color: #2563eb;
        font-weight: bold;
    }

    .status-assigned {
        color: #9333ea;
        font-weight: bold;
    }

    .status-submitted {
        color: #d97706;
        font-weight: bold;
    }

    .status-released {
        color: #16a34a;
        font-weight: bold;
    }

    .status-held {
        color: #dc2626;
        font-weight: bold;
    }

    .small-text {
        color: #6b7280;
        font-size: 14px;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================

if "submission_result" not in st.session_state:
    st.session_state.submission_result = None

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()


# ============================================================
# API HELPER
# ============================================================

def api_get(endpoint):

    try:

        response = requests.get(
            f"{API_URL}{endpoint}",
            timeout=60
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.Timeout:

        st.error(
            "The blockchain request is taking longer than expected. Please try again."
        )

        return None

    except requests.exceptions.RequestException as e:

        st.error(
            f"API Error: {str(e)}"
        )

        return None


def api_post(endpoint, data=None, files=None):

    try:

        response = requests.post(
            f"{API_URL}{endpoint}",
            data=data,
            files=files,
            timeout=120
        )

        return response

    except requests.exceptions.ConnectionError:

        st.error(
            "❌ Cannot connect to the Trustlance backend."
        )

        return None

    except Exception as e:

        st.error(f"API Error: {str(e)}")

        return None


# ============================================================
# GET ALL JOBS
# ============================================================

# ============================================================
# GET ALL JOBS
# ============================================================

@st.cache_data(ttl=10)
def get_all_jobs():

    try:

        response = requests.get(
            f"{API_URL}/api/jobs/",
            timeout=60
        )

        if response.status_code == 200:

            data = response.json()

            return data.get("jobs", [])

        else:

            return []

    except requests.exceptions.Timeout:

        return []

    except requests.exceptions.ConnectionError:

        return []

    except Exception as e:

        print(f"Get jobs error: {e}")

        return []
 
 # ============================================================
# GET reputation
# ============================================================
   
    
@st.cache_data(ttl=10)
def get_reputation(freelancer_address):

    try:

        response = requests.get(
            f"{API_URL}/api/reputation/{freelancer_address}",
            timeout=20
        )

        if response.status_code == 200:

            return response.json()

        return None

    except Exception as e:

        st.error(
            f"Could not fetch reputation: {str(e)}"
        )

        return None
    
# ============================================================
# GET SINGLE JOB
# ============================================================

@st.cache_data(ttl=5)
def get_job(job_id):

    try:

        data = api_get(
            f"/api/jobs/{job_id}"
        )

        # API request failed
        if not data:

            return None

        # API returned an error dictionary
        if not data.get("success"):

            return None

        # Return the job
        return data.get("job")

    except Exception as e:

        print(
            f"Get job error: {e}"
        )

        return None


# ============================================================
# JOB STATUS
# ============================================================

def get_status_info(status):

    status_map = {

        0: {
            "name": "Created",
            "icon": "🟦",
            "description":
                "The job has been created and is waiting for a freelancer."
        },

        1: {
            "name": "Freelancer Assigned",
            "icon": "🟪",
            "description":
                "A freelancer has been assigned and can submit work."
        },

        2: {
            "name": "Work Submitted",
            "icon": "🟨",
            "description":
                "Work has been submitted and is waiting for AI Oracle verification."
        },

        3: {
            "name": "Payment Released",
            "icon": "🟢",
            "description":
                "The AI verification passed and the job was approved."
        },

        4: {
            "name": "Payment Held",
            "icon": "🔴",
            "description":
                "The AI verification did not meet the required threshold."
        }

    }

    return status_map.get(
        status,
        {
            "name": "Unknown",
            "icon": "⚪",
            "description": "Unknown job status."
        }
    )
    
#===========================================
#CHECK JOB EXISTS
#===========================================

def check_job_exists(job_id):

    try:

        response = requests.get(
            f"{API_URL}/api/jobs/{job_id}",
            timeout=15
        )

        if response.status_code == 200:

            data = response.json()

            return data.get("job")

        # 404 means the Job ID is available
        if response.status_code == 404:

            return None

        st.error(
            f"Unable to check Job ID. "
            f"Backend returned {response.status_code}"
        )

        return "ERROR"

    except Exception as e:

        st.error(
            f"Could not connect to backend: {str(e)}"
        )

        return "ERROR"
# ============================================================
# STATUS BADGE
# ============================================================

def show_status(status):

    info = get_status_info(status)

    st.markdown(
        f"### {info['icon']} {info['name']}"
    )

    st.caption(info["description"])


# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="hero">

<h1>🔐 Trustlance</h1>

<p>
Decentralized Freelancing Platform powered by
Blockchain Escrow • IPFS • AI Oracle
</p>

</div>
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("# 🔐 Trustlance")

    st.caption(
        "Blockchain-powered freelance marketplace"
    )

    st.divider()

    page = st.radio(

        "Navigation",

        [
            "🏠 Dashboard",
            "➕ Create Job",
            "🔎 Browse Jobs",
            "👤 Assign Freelancer",
            "📤 Submit Work",
            "📊 Job Status",
            "🏆 My Reputation"
        ]

    )

    st.divider()

    st.markdown("### 🔗 Network Status")

    try:

        data = api_get("/api/jobs/status/test")

        if data and data.get("success"):

            if data.get("blockchain_connected"):

                st.success("🟢 Backend Connected")

            else:

                st.warning("🟡 Backend Connected — Blockchain Offline")

        else:

            st.error("🔴 Backend Offline")

    except Exception as e:

        st.error("🔴 Backend Offline")

    st.divider()

    st.caption(
        "Blockchain • IPFS • AI Oracle"
    )


# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    st.title("Dashboard")

    st.write(
        "Monitor jobs, submissions and AI verification "
        "across the Trustlance platform."
    )

    if st.button("🔄 Refresh Dashboard"):

        get_all_jobs.clear()

        st.rerun()

    jobs = get_all_jobs()

    ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


    # Total jobs
    total_jobs = len(jobs)


    # Freelancer was assigned at some point
    assigned = len([
        j for j in jobs
        if j.get("status") in [1, 2, 3, 4]
    ])


    # Work was submitted at some point
    submitted = len([
        j for j in jobs
        if j.get("status") in [2, 3, 4]
    ])


    # Currently waiting for AI Oracle
    ai_pending = len([
        j for j in jobs
        if j.get("status") == 2
    ])


    # Successfully released
    released = len([
        j for j in jobs
        if j.get("status") == 3
    ])


    # Held after AI verification
    held = len([
        j for j in jobs
        if j.get("status") == 4
    ])

    col1, col2, col3, col4, col5, col6 = st.columns(6)


    col1.metric(
        "📁 Total Jobs",
        total_jobs
    )


    col2.metric(
        "👤 Assigned",
        assigned
    )


    col3.metric(
        "📤 Submitted",
        submitted
    )


    col4.metric(
        "🤖 AI Pending",
        ai_pending
    )


    col5.metric(
        "✅ Released",
        released
    )


    col6.metric(
        "⛔ Held",
        held
    )

    st.divider()

    st.subheader("📋 Recent Jobs")

    if not jobs:

        st.info(
            "No jobs have been created yet."
        )

    else:

        recent_jobs = sorted(
            jobs,
            key=lambda x: x.get("id", 0),
            reverse=True
        )[:6]

        for job in recent_jobs:

            status_info = get_status_info(
                job["status"]
            )

            with st.container():

                col1, col2 = st.columns(
                    [4, 1]
                )

                with col1:

                    st.markdown(
                        f"### Job #{job['id']}"
                    )

                    st.write(
                        job["job_brief"]
                    )

                    st.caption(
                        f"Submission Type: "
                        f"{job.get('submission_type') or 'Not submitted'}"
                    )

                with col2:

                    st.markdown(
                        f"### {status_info['icon']}"
                    )

                    st.write(
                        status_info["name"]
                    )

                st.divider()


# ============================================================
# CREATE JOB
# ============================================================

elif page == "➕ Create Job":

    st.title("➕ Create a New Job")

    st.write(
        "Create a freelance job and securely lock "
        "the payment in blockchain escrow."
    )

    st.info(
        "💡 Choose a unique Job ID. "
        "If the ID already exists, the job will not be created."
    )

    with st.form("create_job_form"):

        job_id = st.number_input(

            "Job ID",

            min_value=1,

            step=1

        )

        job_title = st.text_area(

            "Job Description",

            placeholder=(
                "Example: Write a professional explanation "
                "of how blockchain escrow protects clients "
                "and freelancers."
            ),

            height=150

        )

        ai_threshold = st.slider(

            "AI Verification Threshold",

            min_value=0,

            max_value=100,

            value=20,

            help=(
                "The AI score must meet or exceed this "
                "threshold for approval."
            )

        )

        payment_pol = st.number_input(

            "Escrow Payment (POL)",

            min_value=0.0001,

            value=0.001,

            step=0.001,

            format="%.4f"

        )

        submitted = st.form_submit_button(
            "🔐 Create Job & Lock Payment",
            use_container_width=True
        )

    if submitted:

        if not job_title.strip():

            st.error(
                "❌ Please enter a job description."
            )

        else:

            # --------------------------------------------
            # CHECK EXISTING JOB
            # --------------------------------------------

            existing_job = check_job_exists(int(job_id))

            if existing_job == "ERROR":

                st.stop()


            elif existing_job is not None:

                st.error(
                    f"❌ Job ID {int(job_id)} already exists."
                )

                st.warning(
                    "Please choose a different Job ID."
                )

                show_status(
                    existing_job.get("status", 0)
                )

            else:

                with st.spinner(
                    "Creating job and locking payment on blockchain..."
                ):

                    response = api_post(

                        "/api/jobs/create",

                        data={

                            "job_id": int(job_id),

                            "job_title": job_title.strip(),

                            "ai_threshold": int(ai_threshold),

                            "payment_pol": payment_pol

                        }

                    )

                if response:

                    try:

                        result = response.json()

                    except Exception:

                        result = {}

                    if response.status_code == 200:

                        st.success(
                            "🎉 Job created successfully!"
                        )

                        st.markdown(
                            "### 🔐 Escrow Payment Locked"
                        )

                        job = result.get("job", {})

                        col1, col2, col3 = st.columns(3)

                        col1.metric(
                            "Job ID",
                            job.get("id")
                        )

                        col2.metric(
                            "Payment",
                            f"{job.get('amount_pol')} POL"
                        )

                        col3.metric(
                            "AI Threshold",
                            f"{job.get('threshold')}%"
                        )

                        st.markdown(
                            "### ⛓ Blockchain Transaction"
                        )

                        st.code(
                            result.get(
                                "transaction_hash",
                                ""
                            )
                        )

                        explorer_url = result.get(
                            "explorer_url"
                        )

                        if explorer_url:

                            st.link_button(
                                "🔗 View Transaction on PolygonScan",
                                explorer_url
                            )

                        st.info(
                            "Next step: Assign a freelancer "
                            "to this job."
                        )

                        get_all_jobs.clear()

                    else:

                        st.error(
                            result.get(
                                "detail",
                                "❌ Job creation failed."
                            )
                        )


# ============================================================
# BROWSE JOBS
# ============================================================

elif page == "🔎 Browse Jobs":

    st.title("🔎 Browse Jobs")

    st.write(
        "View all jobs currently stored on the blockchain."
    )

    if st.button("🔄 Refresh Jobs"):

        get_all_jobs.clear()

        st.rerun()

    jobs = get_all_jobs()

    if not jobs:

        st.info(
            "No jobs found."
        )

    else:

        search = st.text_input(
            "🔍 Search jobs",
            placeholder="Search by Job ID or description..."
        )

        filtered_jobs = jobs

        if search:

            search_lower = search.lower()

            filtered_jobs = [

                job for job in jobs

                if (
                    search_lower in str(job["id"]).lower()
                    or
                    search_lower in job[
                        "job_brief"
                    ].lower()
                )

            ]

        filtered_jobs = sorted(
            filtered_jobs,
            key=lambda x: x.get("id", 0),
            reverse=True
        )

        st.caption(
            f"{len(filtered_jobs)} job(s) found"
        )

        for job in filtered_jobs:

            status_info = get_status_info(
                job["status"]
            )

            with st.expander(

                f"{status_info['icon']} "
                f"Job #{job['id']} — "
                f"{status_info['name']}",

                expanded=False

            ):

                col1, col2 = st.columns(2)

                with col1:

                    st.markdown("#### 📋 Job Details")

                    st.write(
                        job["job_brief"]
                    )

                    st.write(
                        f"**Job ID:** {job['id']}"
                    )

                    st.write(
                        f"**Payment:** "
                        f"{job.get('amount_pol', '0')} POL"
                    )

                    st.write(
                        f"**AI Threshold:** "
                        f"{job['threshold']}%"
                    )

                with col2:

                    st.markdown("#### 📊 Current Status")

                    show_status(
                        job["status"]
                    )

                    freelancer = job.get(
                        "freelancer"
                    )

                    if (
                        freelancer
                        and freelancer
                        != "0x0000000000000000000000000000000000000000"
                    ):

                        st.write(
                            f"**Freelancer:** "
                            f"`{freelancer}`"
                        )

                    else:

                        st.warning(
                            "No freelancer assigned yet."
                        )

                    submission_type = job.get(
                        "submission_type"
                    )

                    if submission_type:

                        st.write(
                            f"**Submission Type:** "
                            f"{submission_type.upper()}"
                        )

                    score = job.get("ai_score", 0)

                    if job["status"] in [3, 4]:

                        st.metric(
                            "AI Score",
                            f"{score}/100"
                        )

                cid = job.get("ipfs_cid")

                if cid:

                    st.markdown(
                        "#### 📦 IPFS Submission"
                    )

                    st.code(cid)


# ============================================================
# ASSIGN FREELANCER
# ============================================================

elif page == "👤 Assign Freelancer":

    st.title("👤 Assign Freelancer")

    st.write(
        "Assign a freelancer to an existing Trustlance job."
    )

    with st.form("assign_freelancer_form"):

        job_id = st.number_input(

            "Job ID",

            min_value=1,

            step=1

        )

        freelancer_address = st.text_input(

            "Freelancer Wallet Address",

            placeholder="0x..."

        )

        assign = st.form_submit_button(

            "👤 Assign Freelancer",

            use_container_width=True

        )

    if assign:

        if not freelancer_address.strip():

            st.error(
                "❌ Please enter a freelancer wallet address."
            )

        elif not freelancer_address.startswith("0x"):

            st.error(
                "❌ Please enter a valid wallet address."
            )

        else:

            with st.spinner(
                "Assigning freelancer on blockchain..."
            ):

                response = api_post(

                    "/api/jobs/assign-freelancer",

                    data={

                        "job_id": int(job_id),

                        "freelancer_address":
                        freelancer_address.strip()

                    }

                )

            if response:

                try:

                    result = response.json()

                except Exception:

                    result = {}

                if response.status_code == 200:

                    st.success(
                        "🎉 Freelancer assigned successfully!"
                    )

                    job = result.get("job", {})

                    st.json(job)

                    get_all_jobs.clear()

                else:

                    st.error(
                        result.get(
                            "detail",
                            "Failed to assign freelancer."
                        )
                    )


# ============================================================
# SUBMIT WORK
# ============================================================

elif page == "📤 Submit Work":

    st.title("📤 Submit Your Work")

    st.write(
        "Upload completed work to IPFS and submit "
        "it to the blockchain."
    )

    st.info(
        """
Before submitting work:

1. The Job ID must exist.
2. A freelancer must be assigned.
3. The configured wallet must be the assigned freelancer.
4. The job must have status **Freelancer Assigned**.
5. The AI Oracle Service must be running to verify the submission.
        """
    )

    job_id = st.number_input(

        "Job ID",

        min_value=1,

        step=1

    )

    submission_type = st.selectbox(

        "Submission Type",

        [
            "text",
            "code",
            "image",
            "audio"
        ]

    )

    file_types = {

        "text": [
            "txt"
        ],

        "code": [
            "py",
            "js",
            "java",
            "cpp",
            "c"
        ],

        "image": [
            "png",
            "jpg",
            "jpeg"
        ],

        "audio": [
            "mp3",
            "wav",
            "m4a"
        ]

    }

    uploaded_file = st.file_uploader(

        f"Upload {submission_type.upper()} File",

        type=file_types[submission_type]

    )

    if uploaded_file:

        st.success(
            f"📄 {uploaded_file.name} selected"
        )

        col1, col2 = st.columns(2)

        col1.write(
            f"**File Type:** "
            f"{submission_type.upper()}"
        )

        col2.write(
            f"**File Size:** "
            f"{uploaded_file.size / 1024:.2f} KB"
        )

    if st.button(

        "🚀 Upload & Submit Work",

        use_container_width=True,

        type="primary"

    ):

        if not uploaded_file:

            st.error(
                "❌ Please upload a file."
            )

        else:

            with st.spinner(

                "Uploading to IPFS and submitting to blockchain..."

            ):

                files = {

                    "file": (

                        uploaded_file.name,

                        uploaded_file.getvalue(),

                        uploaded_file.type

                    )

                }

                data = {

                    "job_id": str(int(job_id)),

                    "submission_type": submission_type

                }

                response = api_post(

                    "/api/submissions/",

                    data=data,

                    files=files

                )

            if response:

                try:

                    result = response.json()

                except Exception:

                    result = {}

                if response.status_code == 200:

                    st.success(
                        "🎉 Work submitted successfully!"
                    )

                    st.session_state.submission_result = {

                        "job_id": int(job_id),

                        "submission_type": submission_type,

                        "result": result,

                        "submitted_at": datetime.now()

                    }

                    get_all_jobs.clear()

                    time.sleep(1)

                    st.rerun()

                else:

                    detail = result.get(
                        "detail",
                        "Submission failed."
                    )

                    st.error(
                        f"❌ {detail}"
                    )


    # ========================================================
    # SUBMISSION DETAILS
    # ========================================================

    if st.session_state.submission_result:

        submission = (
            st.session_state.submission_result
        )

        result = submission["result"]

        st.divider()

        st.subheader("📦 Submission Details")

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Job ID",
                submission["job_id"]
            )

            st.metric(
                "Submission Type",
                submission["submission_type"].upper()
            )

        with col2:

            st.metric(
                "Submission Status",
                "Submitted"
            )

            st.caption(
                f"Submitted at "
                f"{submission['submitted_at'].strftime('%H:%M:%S')}"
            )

        cid = (

            result.get("ipfs_cid")

            or result.get("cid")

            or result.get("submission_cid")

        )

        if cid:

            st.markdown("### 📦 IPFS CID")

            st.code(cid)

        tx_hash = (

            result.get("transaction_hash")

            or result.get("tx_hash")

        )

        if tx_hash:

            st.markdown(
                "### ⛓ Blockchain Transaction"
            )

            st.code(tx_hash)

        st.divider()

        # ====================================================
        # LIVE ORACLE STATUS
        # ====================================================

        st.subheader("🤖 AI Oracle Verification")

        st.write(
            "Checking the latest job status from blockchain..."
        )

        if st.button(
            "🔄 Check Oracle Result",
            key="check_oracle"
        ):

            get_all_jobs.clear()

            st.rerun()

        current_job = get_job(
            submission["job_id"]
        )

        if current_job:

            status = current_job.get(
                "status"
            )

            score = current_job.get(
                "ai_score",
                0
            )

            status_info = get_status_info(
                status
            )

            if status == 2:

                st.warning(
                    "⏳ **Waiting for AI Oracle verification**"
                )

                st.write(
                    "The Oracle Service has not finished "
                    "processing this submission yet."
                )

                st.info(
                    "Keep the Oracle Service running and "
                    "click **Check Oracle Result** after a few seconds."
                )

            elif status == 3:

                st.success(
                    "🎉 **AI Verification Completed — APPROVED**"
                )

                st.metric(
                    "Final AI Score",
                    f"{score}/100"
                )

                st.success(
                    "The submission passed AI verification "
                    "and the job has been approved."
                )

            elif status == 4:

                st.error(
                    "⛔ **AI Verification Completed — HELD**"
                )

                st.metric(
                    "Final AI Score",
                    f"{score}/100"
                )

                st.warning(
                    "The submission did not meet the required "
                    "AI verification threshold."
                )

            else:

                show_status(status)

        else:

            st.warning(
                "Unable to fetch the latest job status."
            )

# ============================================================
# FREELANCER REPUTATION
# ============================================================

elif page == "🏆 My Reputation":

    st.title("🏆 Freelancer Reputation")

    st.write(
        "View your blockchain-based Trustlance reputation "
        "and AI verification performance."
    )

    st.divider()

    freelancer_address = st.text_input(
        "👛 Enter Freelancer Wallet Address",
        placeholder="0x..."
    )

    if st.button(
        "🔍 View Reputation",
        use_container_width=True
    ):

        if not freelancer_address:

            st.warning(
                "⚠️ Please enter a freelancer wallet address."
            )

        else:

            with st.spinner(
                "Fetching reputation from blockchain..."
            ):

                data = get_reputation(
                    freelancer_address
                )

            if not data:

                st.error(
                    "❌ Could not fetch freelancer reputation."
                )

            elif not data.get("success"):

                st.error(
                    "❌ Reputation data was not available."
                )

            else:

                completed_jobs = data.get(
                    "completed_jobs",
                    0
                )

                total_ai_score = data.get(
                    "total_ai_score",
                    0
                )

                average_ai_score = data.get(
                    "average_ai_score",
                    0
                )

                freelancer = data.get(
                    "freelancer",
                    freelancer_address
                )

                st.success(
                    "🏆 Reputation loaded successfully!"
                )

                st.divider()

                # ------------------------------------------------
                # FREELANCER WALLET
                # ------------------------------------------------

                st.subheader(
                    "👤 Freelancer"
                )

                st.code(
                    freelancer
                )

                st.divider()

                # ------------------------------------------------
                # REPUTATION METRICS
                # ------------------------------------------------

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "🏆 Completed Jobs",
                    completed_jobs
                )

                col2.metric(
                    "🤖 Average AI Score",
                    f"{average_ai_score}/100"
                )

                col3.metric(
                    "⭐ Total AI Score",
                    total_ai_score
                )

                st.divider()

                # ------------------------------------------------
                # REPUTATION STATUS
                # ------------------------------------------------

                st.subheader(
                    "🎖️ Trustlance Reputation"
                )

                if completed_jobs == 0:

                    st.info(
                        "No completed jobs yet. "
                        "Complete AI-verified jobs to build your reputation."
                    )

                elif average_ai_score >= 80:

                    st.success(
                        "🌟 Excellent Reputation"
                    )

                    st.write(
                        "This freelancer has consistently achieved "
                        "strong AI verification scores."
                    )

                elif average_ai_score >= 60:

                    st.success(
                        "✅ Good Reputation"
                    )

                    st.write(
                        "This freelancer has successfully completed "
                        "AI-verified work on Trustlance."
                    )

                elif average_ai_score >= 40:

                    st.warning(
                        "🟡 Developing Reputation"
                    )

                    st.write(
                        "Continue completing high-quality jobs "
                        "to improve reputation."
                    )

                else:

                    st.warning(
                        "🔸 New / Low Reputation"
                    )

                    st.write(
                        "More successful AI-verified jobs are needed "
                        "to build reputation."
                    )

                st.divider()

                # ------------------------------------------------
                # SOULBOUND NFT
                # ------------------------------------------------

                st.subheader(
                    "🔐 Soulbound Reputation NFT"
                )

                st.info(
                    "Trustlance reputation is recorded using "
                    "non-transferable Soulbound NFTs."
                )

                st.write(
                    "🏆 Reputation is earned through successful "
                    "AI-verified job completion."
                )

                st.write(
                    "🔒 Reputation credentials cannot be transferred "
                    "to another wallet."
                )
# ============================================================
# JOB STATUS PAGE
# ============================================================

elif page == "📊 Job Status":

    st.title("📊 Track Job Status")

    st.write(
        "Check the latest blockchain status, submission details "
        "and AI verification result."
    )

    job_id = st.number_input(
        "Enter Job ID",
        min_value=1,
        step=1
    )

    if st.button(
        "🔍 Check Job Status",
        use_container_width=True
    ):

        with st.spinner(
            "Fetching job from blockchain..."
        ):
            job = get_job(
                int(job_id)
            )

        # ====================================================
        # JOB NOT FOUND
        # ====================================================

        if not job:

            st.error(
                f"❌ Job #{job_id} was not found."
            )

        else:

            status = job.get("status", 0)

            score = job.get("ai_score", 0)

            threshold = job.get("threshold", 0)

            status_info = get_status_info(status)

            # ====================================================
            # JOB FOUND
            # ====================================================

            st.success(
                f"✅ Job #{job['id']} found successfully"
            )

            # ====================================================
            # MAIN METRICS
            # ====================================================

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "🆔 Job ID",
                job["id"]
            )

            col2.metric(
                "💰 Payment",
                f"{job.get('amount_pol', '0')} POL"
            )

            col3.metric(
                "🤖 AI Score",
                f"{score}/100"
            )

            col4.metric(
                "🎯 Threshold",
                f"{threshold}/100"
            )

            st.divider()

            # ====================================================
            # CURRENT STATUS
            # ====================================================

            st.subheader("📊 Current Status")

            show_status(status)

            st.caption(
                f"Current blockchain status: "
                f"{status_info['name']}"
            )

            # ====================================================
            # ORACLE RESULT
            # ====================================================

            if status == 0:

                st.info(
                    "📝 Job has been created and is waiting "
                    "for a freelancer."
                )

            elif status == 1:

                st.info(
                    "👤 Freelancer has been assigned. "
                    "The freelancer can now submit the work."
                )

            elif status == 2:

                st.warning(
                    "⏳ Work Submitted — Waiting for AI Oracle verification."
                )

                st.info(
                    "The submission is stored on IPFS and recorded "
                    "on the blockchain. The Oracle Service will "
                    "automatically process the submission."
                )

            elif status == 3:

                st.success(
                    "🎉 Payment Released!"
                )

                st.success(
                    f"AI verification passed with a score of "
                    f"{score}/100."
                )

                st.info(
                    f"Required threshold was {threshold}/100."
                )

            elif status == 4:

                st.error(
                    "⛔ Payment Held"
                )

                st.warning(
                    f"AI Score: {score}/100 | "
                    f"Required Threshold: {threshold}/100"
                )

                st.info(
                    "The submission did not meet the required "
                    "AI verification threshold."
                )

            st.divider()

            # ====================================================
            # JOB DESCRIPTION
            # ====================================================

            st.subheader("📋 Job Description")

            st.write(
                job.get(
                    "job_brief",
                    "No job description available."
                )
            )

            st.divider()

            # ====================================================
            # JOB LIFECYCLE
            # ====================================================

            st.subheader("🔄 Job Lifecycle")

            lifecycle = [
                "📝 Job Created",
                "👤 Freelancer Assigned",
                "📤 Work Submitted",
                "🤖 AI Verified",
                "💰 Payment Released / Held"
            ]

            if status == 0:

                current_step = 1

            elif status == 1:

                current_step = 2

            elif status == 2:

                current_step = 3

            elif status in [3, 4]:

                current_step = 5

            else:

                current_step = 0

            for index, step in enumerate(
                lifecycle,
                start=1
            ):

                if index <= current_step:

                    st.success(
                        f"✅ {step}"
                    )

                else:

                    st.info(
                        f"⬜ {step}"
                    )

            st.divider()

            # ====================================================
            # PARTICIPANTS
            # ====================================================

            st.subheader("👥 Job Participants")

            client = job.get("client")

            freelancer = job.get("freelancer")

            col1, col2 = st.columns(2)

            with col1:

                st.markdown(
                    "**👤 Client Wallet**"
                )

                if client:

                    st.code(client)

                else:

                    st.warning(
                        "Client information unavailable."
                    )

            with col2:

                st.markdown(
                    "**💼 Freelancer Wallet**"
                )

                if (
                    freelancer
                    and freelancer
                    != "0x0000000000000000000000000000000000000000"
                ):

                    st.code(freelancer)

                else:

                    st.warning(
                        "No freelancer assigned yet."
                    )

            # ====================================================
            # SUBMISSION DETAILS
            # ====================================================

            cid = job.get("ipfs_cid")

            submission_type = job.get(
                "submission_type",
                ""
            )

            if cid:

                st.divider()

                st.subheader(
                    "📦 Submission Details"
                )

                col1, col2 = st.columns(2)

                with col1:

                    st.markdown(
                        "**Submission Type**"
                    )

                    st.code(
                        submission_type.upper()
                    )

                with col2:

                    st.markdown(
                        "**IPFS CID**"
                    )

                    st.code(cid)

                # ------------------------------------------------
                # IPFS LINK
                # ------------------------------------------------

                ipfs_url = (
                    f"https://ipfs.io/ipfs/{cid}"
                )

                st.link_button(
                    "🌐 View Submission on IPFS",
                    ipfs_url,
                    use_container_width=True
                )

            else:

                st.divider()

                st.info(
                    "📭 No work has been submitted yet."
                )

# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown("""
<center>

<b>🔐 Trustlance</b><br>

Decentralized Freelancing • Blockchain Escrow • IPFS • AI Oracle

</center>
""", unsafe_allow_html=True)