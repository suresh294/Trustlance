import sys
import os
from pathlib import Path
import json
from PIL import Image


AI_DIR = Path(__file__).resolve().parent

CODE_CONFIG_FILE = AI_DIR / "code_job_configs.json"


def get_code_job_config(job_id):
    """
    Loads the code requirements for a job.

    Currently reads from JSON.
    Later FastAPI/frontend will save this configuration
    automatically when the client creates a code job.
    """

    if not CODE_CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Code configuration file not found: {CODE_CONFIG_FILE}"
        )

    with open(
        CODE_CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        configs = json.load(f)

    config = configs.get(str(job_id))

    if not config:
        raise ValueError(
            f"No code test configuration found for job {job_id}."
        )

    if "function_name" not in config:
        raise ValueError(
            f"function_name missing for job {job_id}"
        )

    if "test_cases" not in config:
        raise ValueError(
            f"test_cases missing for job {job_id}"
        )

    # Convert JSON lists back to Python tuples.
    test_cases = [
        (tuple(test_input), expected_output)
        for test_input, expected_output
        in config["test_cases"]
    ]

    return {
        "function_name": config["function_name"],
        "test_cases": test_cases
    }
# ============================================================
# PROJECT PATH
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = BASE_DIR / "downloads"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

#==========================================================

# ============================================================
# SUBMISSION TYPE VALIDATION
# ============================================================

def validate_image_submission(file_path):
    """
    Verify that the downloaded submission is a real image.
    """

    try:

        with Image.open(file_path) as image:

            image.verify()

        return True

    except Exception as e:

        raise ValueError(
            f"Submission type mismatch: blockchain says IMAGE, "
            f"but downloaded content is not a valid image. "
            f"File: {file_path}"
        ) from e


def validate_audio_submission(file_path):
    """
    Basic validation that the downloaded audio file is not empty.

    The audio checker/Whisper performs the actual audio decoding.
    """

    file_path = Path(file_path)

    if not file_path.exists():

        raise ValueError(
            f"Audio submission file does not exist: {file_path}"
        )

    if file_path.stat().st_size == 0:

        raise ValueError(
            "Submission type mismatch: blockchain says AUDIO, "
            "but downloaded file is empty."
        )

    return True

# ============================================================
# IMPORTS
# ============================================================

from web3 import Web3

from backend.ai.ai_dispatcher import process_ai_submission

from backend.oracle.oracle_bridge import (
    report_score_to_blockchain,
    get_web3,
    load_contract_abi,
    ESCROW_ADDRESS,
)

from backend.ipfs.ipfs_upload import (
    download_from_ipfs,
    download_file_from_ipfs,
)


# ============================================================
# CONSTANTS
# ============================================================

VALID_SUBMISSION_TYPES = {
    "text",
    "code",
    "image",
    "audio",
}


# ============================================================
# GET JOB DETAILS FROM BLOCKCHAIN
# ============================================================

def get_job_details(job_id: int) -> dict:
    """
    Fetches all required job information directly from the
    deployed FreelanceEscrow contract.

    Job tuple indexes:

    job[0] = jobId
    job[1] = client
    job[2] = freelancer
    job[3] = amount
    job[4] = threshold
    job[5] = jobTitle
    job[6] = ipfsCID
    job[7] = submissionType
    job[8] = aiScore
    job[9] = status
    """

    w3 = get_web3()
    abi = load_contract_abi()

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(ESCROW_ADDRESS),
        abi=abi
    )

    job = contract.functions.getJob(job_id).call()

    return {
        "job_id": job[0],
        "client": job[1],
        "freelancer": job[2],
        "amount": job[3],
        "threshold": job[4],
        "job_brief": job[5],
        "ipfs_cid": job[6],
        "submission_type": job[7],
        "ai_score": job[8],
        "status": job[9],
    }


# ============================================================
# VALIDATE JOB
# ============================================================

def validate_job_for_ai(details: dict):
    """
    Ensures the job is ready for AI verification.

    Status values:

    0 = Open
    1 = Assigned
    2 = Submitted
    3 = Held
    4 = Released
    5 = Refunded
    """

    if details["status"] != 2:
        raise ValueError(
            f"Job is not ready for AI verification. "
            f"Expected status 2 (Submitted), "
            f"got {details['status']}."
        )

    if not details["ipfs_cid"]:
        raise ValueError(
            "No IPFS CID found for this job."
        )

    if not details["submission_type"]:
        raise ValueError(
            "No submission type found for this job."
        )

    submission_type = details["submission_type"].lower().strip()

    if submission_type not in VALID_SUBMISSION_TYPES:
        raise ValueError(
            f"Unsupported submission type: {submission_type}. "
            f"Supported types: {', '.join(sorted(VALID_SUBMISSION_TYPES))}"
        )


# ============================================================
# CODE JOB CONFIGURATION
# ============================================================

def get_code_job_config(job_id: int) -> dict:
    """
    Loads code job configuration from the separate JSON file.
    """

    if not CODE_CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Code configuration file not found: {CODE_CONFIG_FILE}"
        )

    with open(
        CODE_CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        configs = json.load(f)

    config = configs.get(str(job_id))

    if not config:
        raise ValueError(
            f"No code test configuration found for job {job_id}."
        )

    if "function_name" not in config:
        raise ValueError(
            f"function_name missing for job {job_id}"
        )

    if "test_cases" not in config:
        raise ValueError(
            f"test_cases missing for job {job_id}"
        )

    test_cases = [
        (tuple(test_input), expected_output)
        for test_input, expected_output
        in config["test_cases"]
    ]

    return {
        "function_name": config["function_name"],
        "test_cases": test_cases
    }

   

    

# ============================================================
# RUN AI VERIFICATION
# ============================================================

def run_ai_verification(
    job_id: int,
    preview: bool = False
):
    """
    Universal Trustlance AI Oracle Pipeline.

    Automatically:

    1. Fetches job from blockchain
    2. Reads submissionType
    3. Downloads submission from IPFS
    4. Routes to correct AI checker
    5. Calculates score
    6. Reports score to blockchain

    Supported:

        text
        image
        audio
        code
    """

    print("=" * 60)
    print("TRUSTLANCE UNIVERSAL AI ORACLE PIPELINE")
    print("=" * 60)

    # --------------------------------------------------------
    # STEP 1: FETCH JOB
    # --------------------------------------------------------

    print(f"\nFetching job details from blockchain for job {job_id}...")

    details = get_job_details(job_id)

    validate_job_for_ai(details)

    submission_type = (
        details["submission_type"]
        .lower()
        .strip()
    )

    freelancer = details["freelancer"]
    threshold = details["threshold"]
    job_brief = details["job_brief"]
    submission_cid = details["ipfs_cid"]

    print(f"  Job ID:                     {details['job_id']}")
    print(f"  Client:                     {details['client']}")
    print(f"  Freelancer:                 {freelancer}")
    print(f"  Job brief:                  {job_brief}")
    print(f"  Threshold:                  {threshold}")
    print(f"  Submission CID:             {submission_cid}")
    print(f"  Submission type:            {submission_type}")
    print(f"  Current AI score:           {details['ai_score']}")
    print(f"  Current job status:         {details['status']}")

    # --------------------------------------------------------
    # COMMON ARGUMENTS
    # --------------------------------------------------------

    common_args = {
        "job_id": str(job_id),
        "job_brief": job_brief,
        "freelancer": freelancer,
        "threshold": threshold,
        "cid": submission_cid,
        "preview": preview,
    }

    # --------------------------------------------------------
    # STEP 2: TEXT
    # --------------------------------------------------------

    if submission_type == "text":

        print("\nDownloading TEXT submission from IPFS...")

        submission_text = download_from_ipfs(
            submission_cid
        )

        print("Running TEXT AI compliance checker...")

        ai_result = process_ai_submission(
            submission_type="text",
            submission_text=submission_text,
            **common_args
        )

    # --------------------------------------------------------
    # STEP 3: IMAGE
    # --------------------------------------------------------

    elif submission_type == "image":

        print("\nDownloading IMAGE submission from IPFS...")

        image_path = download_file_from_ipfs(
            submission_cid,
            DOWNLOAD_DIR,
            f"job_{job_id}_submission"
        )

        print(f"Downloaded image: {image_path}")

        print("Validating IMAGE submission...")

        validate_image_submission(image_path)

        print("IMAGE validation successful.")

        print("Running IMAGE AI compliance checker...")

        ai_result = process_ai_submission(
            submission_type="image",
            job_description=job_brief,
            image_path=image_path,
            **common_args
        )

    # --------------------------------------------------------
    # STEP 4: AUDIO
    # --------------------------------------------------------

    elif submission_type == "audio":

        print("\nDownloading AUDIO submission from IPFS...")

        audio_path = download_file_from_ipfs(
            submission_cid,
            DOWNLOAD_DIR,
            f"job_{job_id}_submission"
        )

        print(f"Downloaded audio: {audio_path}")

        print("Validating AUDIO submission...")

        validate_audio_submission(audio_path)

        print("AUDIO validation successful.")

        print("Running AUDIO AI compliance checker...")

        ai_result = process_ai_submission(
            submission_type="audio",
            job_description=job_brief,
            audio_path=str(audio_path),
            **common_args
        )

    # --------------------------------------------------------
    # STEP 5: CODE
    # --------------------------------------------------------

    elif submission_type == "code":

        print("\nDownloading CODE submission from IPFS...")

        code = download_from_ipfs(submission_cid)

        print("Loading code job configuration...")

        code_config = get_code_job_config(job_id)

        if code_config is None:
            raise ValueError(
                f"Code configuration returned None for job {job_id}"
            )

        print("Code configuration loaded:")
        print(code_config)

        function_name = code_config.get("function_name")
        test_cases = code_config.get("test_cases")

        if not function_name:
            raise ValueError(
                f"function_name is missing for job {job_id}"
            )

        if not test_cases:
            raise ValueError(
                f"test_cases are missing for job {job_id}"
            )

        print(f"Expected function: {function_name}")
        print("Running CODE AI compliance checker...")

        ai_result = process_ai_submission(
            submission_type="code",
            code=code,
            function_name=function_name,
            test_cases=test_cases,
            **common_args
        )

    else:

        raise ValueError(
            f"Unsupported submission type: "
            f"{submission_type}"
        )

    # --------------------------------------------------------
    # STEP 6: DISPLAY AI RESULT
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("AI VERIFICATION RESULT")
    print("=" * 60)

    print(f"Relevance:    {ai_result.get('relevance')}")
    print(f"Duplication:  {ai_result.get('duplication')}")
    print(f"Final Score:  {ai_result.get('final_score')}")
    print(f"Decision:     {ai_result.get('decision')}")

    # --------------------------------------------------------
    # PREVIEW MODE
    # --------------------------------------------------------

    if preview:

        print("\nPREVIEW MODE ENABLED")
        print("Nothing will be sent to the blockchain.")

        return {
            "job_details": details,
            "ai_result": ai_result,
            "blockchain_result": None,
        }

    # --------------------------------------------------------
    # STEP 7: REPORT SCORE TO BLOCKCHAIN
    # --------------------------------------------------------

    final_score_int = round(
        float(ai_result["final_score"])
    )

    # Safety guarantee: Solidity expects a score from 0 to 100
    final_score_int = max(
        0,
        min(100, final_score_int)
    )

    print("\n" + "=" * 60)
    print("REPORTING SCORE TO BLOCKCHAIN")
    print("=" * 60)

    print(
        f"Reporting score {final_score_int} "
        f"for job {job_id}..."
    )

    blockchain_result = report_score_to_blockchain(
        job_id=job_id,
        ai_score=final_score_int
    )

    print("\nBlockchain result:")
    print(blockchain_result)

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    return {
        "job_details": details,
        "ai_result": ai_result,
        "blockchain_result": blockchain_result,
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # ========================================================
    # CHANGE ONLY THE JOB ID
    #
    # The pipeline automatically gets:
    #
    # - Freelancer
    # - Job brief
    # - Threshold
    # - IPFS CID
    # - Submission type
    #
    # directly from the blockchain.
    # ========================================================

    JOB_ID = 32

    print("=" * 60)
    print("STARTING UNIVERSAL AI ORACLE PIPELINE")
    print("=" * 60)

    result = run_ai_verification(job_id=JOB_ID)

    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)

    print(result)