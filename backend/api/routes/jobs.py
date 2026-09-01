import os
import json
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Form
from dotenv import load_dotenv
from web3 import Web3


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BLOCKCHAIN_DIR = PROJECT_ROOT / "blockchain"

ENV_PATH = BLOCKCHAIN_DIR / ".env"

ARTIFACT_PATH = (
    BLOCKCHAIN_DIR
    / "artifacts"
    / "contracts"
    / "FreelanceEscrow.sol"
    / "FreelanceEscrow.json"
)


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(ENV_PATH)

RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")


if not RPC_URL:
    raise ValueError(
        "RPC_URL is missing from blockchain/.env"
    )


if not PRIVATE_KEY:
    raise ValueError(
        "PRIVATE_KEY is missing from blockchain/.env"
    )


# ============================================================
# ESCROW CONTRACT
# ============================================================

ESCROW_ADDRESS = "0x9AF814D18DD67B09CceA594d54f625fd63D0B870"


# ============================================================
# LOAD ABI
# ============================================================

if not ARTIFACT_PATH.exists():

    raise FileNotFoundError(
        f"Contract artifact not found: {ARTIFACT_PATH}"
    )


with open(
    ARTIFACT_PATH,
    "r",
    encoding="utf-8"
) as file:

    ABI = json.load(file)["abi"]


# ============================================================
# CONNECT TO BLOCKCHAIN
# ============================================================

w3 = Web3(
    Web3.HTTPProvider(
        RPC_URL,
        request_kwargs={
            "timeout": 30
        }
    )
)


if not w3.is_connected():

    raise RuntimeError(
        "Could not connect to Polygon Amoy"
    )


contract = w3.eth.contract(
    address=Web3.to_checksum_address(
        ESCROW_ADDRESS
    ),
    abi=ABI
)


# ============================================================
# CLIENT ACCOUNT
# ============================================================

client_account = w3.eth.account.from_key(
    PRIVATE_KEY
)


# ============================================================
# CACHE SETTINGS
# ============================================================

JOB_CACHE = {
    "jobs": [],
    "timestamp": 0
}


CACHE_DURATION = 30

MAX_JOB_ID = 55


# ============================================================
# CLEAR JOB CACHE
# ============================================================

def clear_job_cache():

    JOB_CACHE["jobs"] = []

    JOB_CACHE["timestamp"] = 0


# ============================================================
# API STATUS TEST
# ============================================================

@router.get("/status/test")
def jobs_status():

    return {

        "success": True,

        "message": "Jobs API is working",

        "blockchain_connected": w3.is_connected(),

        "chain_id": w3.eth.chain_id,

        "client_wallet": client_account.address

    }


# ============================================================
# FORMAT JOB
# ============================================================

def format_job(job):

    return {

        "id": int(job[0]),

        "client": job[1],

        "freelancer": job[2],

        "amount": str(job[3]),

        "amount_pol": str(
            w3.from_wei(
                job[3],
                "ether"
            )
        ),

        "threshold": int(job[4]),

        "job_brief": job[5],

        "ipfs_cid": job[6],

        "submission_type": job[7],

        "ai_score": int(job[8]),

        "status": int(job[9])

    }


# ============================================================
# CREATE JOB
# ============================================================

@router.post("/create")
def create_job(

    job_id: int = Form(...),

    job_title: str = Form(...),

    ai_threshold: int = Form(...),

    payment_pol: float = Form(...)

):

    try:

        # ----------------------------------------------------
        # VALIDATE VALUES
        # ----------------------------------------------------

        if job_id < 0:

            raise HTTPException(
                status_code=400,
                detail="Job ID cannot be negative"
            )


        if len(job_title.strip()) < 5:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Job title must contain "
                    "at least 5 characters"
                )
            )


        if ai_threshold < 0 or ai_threshold > 100:

            raise HTTPException(
                status_code=400,
                detail=(
                    "AI threshold must be "
                    "between 0 and 100"
                )
            )


        if payment_pol <= 0:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment must be greater than 0"
                )
            )


        # ----------------------------------------------------
        # CHECK IF JOB EXISTS
        # ----------------------------------------------------

        existing_job = contract.functions.getJob(
            job_id
        ).call()


        existing_client = existing_job[1]


        if (
            existing_client
            != "0x0000000000000000000000000000000000000000"
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Job ID {job_id} already exists. "
                    "Please choose another Job ID."
                )
            )


        # ----------------------------------------------------
        # CONVERT PAYMENT
        # ----------------------------------------------------

        payment = w3.to_wei(
            payment_pol,
            "ether"
        )


        # ----------------------------------------------------
        # ESTIMATE GAS
        # ----------------------------------------------------

        gas_estimate = contract.functions.createJob(

            job_id,

            job_title.strip(),

            ai_threshold

        ).estimate_gas({

            "from": client_account.address,

            "value": payment

        })


        # ----------------------------------------------------
        # GET NONCE
        # ----------------------------------------------------

        nonce = w3.eth.get_transaction_count(

            client_account.address,

            "pending"

        )


        # ----------------------------------------------------
        # BUILD TRANSACTION
        # ----------------------------------------------------

        transaction = contract.functions.createJob(

            job_id,

            job_title.strip(),

            ai_threshold

        ).build_transaction({

            "from": client_account.address,

            "value": payment,

            "nonce": nonce,

            "gas": gas_estimate + 20000,

            "gasPrice": w3.eth.gas_price,

            "chainId": w3.eth.chain_id

        })


        # ----------------------------------------------------
        # SIGN TRANSACTION
        # ----------------------------------------------------

        signed_transaction = (
            client_account.sign_transaction(
                transaction
            )
        )


        # ----------------------------------------------------
        # SEND TRANSACTION
        # ----------------------------------------------------

        tx_hash = w3.eth.send_raw_transaction(

            signed_transaction.raw_transaction

        )


        # ----------------------------------------------------
        # WAIT FOR CONFIRMATION
        # ----------------------------------------------------

        receipt = w3.eth.wait_for_transaction_receipt(
            tx_hash
        )


        if receipt.status != 1:

            raise HTTPException(
                status_code=500,
                detail="Blockchain job creation failed"
            )


        # ----------------------------------------------------
        # FETCH CREATED JOB
        # ----------------------------------------------------

        job = contract.functions.getJob(
            job_id
        ).call()


        # ----------------------------------------------------
        # CLEAR CACHE
        # ----------------------------------------------------

        clear_job_cache()


        # ----------------------------------------------------
        # SUCCESS RESPONSE
        # ----------------------------------------------------

        return {

            "success": True,

            "message": (
                "Job successfully created and "
                "escrow payment locked on blockchain"
            ),

            "job": format_job(job),

            "transaction_hash": tx_hash.hex(),

            "explorer_url": (
                "https://amoy.polygonscan.com/tx/"
                f"{tx_hash.hex()}"
            )

        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "Create job API error:",
            str(e)
        )


        raise HTTPException(

            status_code=500,

            detail=str(e)

        )


# ============================================================
# ASSIGN FREELANCER
# ============================================================

@router.post("/assign-freelancer")
def assign_freelancer(

    job_id: int = Form(...),

    freelancer_address: str = Form(...)

):

    try:

        zero_address = (
            "0x0000000000000000000000000000000000000000"
        )


        # ----------------------------------------------------
        # GET JOB
        # ----------------------------------------------------

        job = contract.functions.getJob(
            job_id
        ).call()


        # ----------------------------------------------------
        # CHECK JOB EXISTS
        # ----------------------------------------------------

        if job[1] == zero_address:

            raise HTTPException(
                status_code=404,
                detail="Job not found"
            )


        # ----------------------------------------------------
        # VALIDATE ADDRESS
        # ----------------------------------------------------

        if not Web3.is_address(
            freelancer_address
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid freelancer wallet address"
                )
            )


        freelancer_address = (
            Web3.to_checksum_address(
                freelancer_address
            )
        )


        # ----------------------------------------------------
        # CHECK ASSIGNMENT
        # ----------------------------------------------------

        if job[2] != zero_address:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Freelancer is already assigned"
                )
            )


        # ----------------------------------------------------
        # ESTIMATE GAS
        # ----------------------------------------------------

        gas_estimate = (
            contract.functions.assignFreelancer(

                job_id,

                freelancer_address

            ).estimate_gas({

                "from": client_account.address

            })
        )


        # ----------------------------------------------------
        # GET NONCE
        # ----------------------------------------------------

        nonce = w3.eth.get_transaction_count(

            client_account.address,

            "pending"

        )


        # ----------------------------------------------------
        # BUILD TRANSACTION
        # ----------------------------------------------------

        transaction = (
            contract.functions.assignFreelancer(

                job_id,

                freelancer_address

            ).build_transaction({

                "from": client_account.address,

                "nonce": nonce,

                "gas": gas_estimate + 20000,

                "gasPrice": w3.eth.gas_price,

                "chainId": w3.eth.chain_id

            })
        )


        # ----------------------------------------------------
        # SIGN TRANSACTION
        # ----------------------------------------------------

        signed_transaction = (
            client_account.sign_transaction(
                transaction
            )
        )


        # ----------------------------------------------------
        # SEND TRANSACTION
        # ----------------------------------------------------

        tx_hash = w3.eth.send_raw_transaction(

            signed_transaction.raw_transaction

        )


        # ----------------------------------------------------
        # WAIT FOR CONFIRMATION
        # ----------------------------------------------------

        receipt = w3.eth.wait_for_transaction_receipt(
            tx_hash
        )


        if receipt.status != 1:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Freelancer assignment failed"
                )
            )


        # ----------------------------------------------------
        # FETCH UPDATED JOB
        # ----------------------------------------------------

        updated_job = contract.functions.getJob(
            job_id
        ).call()


        # ----------------------------------------------------
        # CLEAR CACHE
        # ----------------------------------------------------

        clear_job_cache()


        return {

            "success": True,

            "message": (
                "Freelancer successfully assigned"
            ),

            "job": format_job(updated_job),

            "transaction_hash": tx_hash.hex(),

            "explorer_url": (
                "https://amoy.polygonscan.com/tx/"
                f"{tx_hash.hex()}"
            )

        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "Assign freelancer API error:",
            str(e)
        )


        raise HTTPException(

            status_code=500,

            detail=str(e)

        )


# ============================================================
# GET ALL JOBS
# ============================================================

@router.get("/")
def get_jobs():

    try:

        current_time = time.time()


        # ----------------------------------------------------
        # RETURN CACHE IF STILL VALID
        # ----------------------------------------------------

        if (

            JOB_CACHE["jobs"]

            and

            current_time - JOB_CACHE["timestamp"]
            < CACHE_DURATION

        ):

            print(
                "Returning jobs from cache"
            )


            return {

                "success": True,

                "count": len(
                    JOB_CACHE["jobs"]
                ),

                "jobs": JOB_CACHE["jobs"],

                "cached": True

            }


        # ----------------------------------------------------
        # FETCH JOBS FROM BLOCKCHAIN
        # ----------------------------------------------------

        print(
            f"Fetching jobs 1 to {MAX_JOB_ID} "
            "from blockchain..."
        )


        jobs = []


        for job_id in range(
            1,
            MAX_JOB_ID + 1
        ):

            try:

                job = contract.functions.getJob(
                    job_id
                ).call()


                formatted_job = format_job(job)


                if (

                    formatted_job["client"]

                    !=

                    "0x0000000000000000000000000000000000000000"

                ):

                    jobs.append(
                        formatted_job
                    )


            except Exception as e:

                print(
                    f"Skipping job {job_id}: {e}"
                )


                continue


        # ----------------------------------------------------
        # SORT NEWEST FIRST
        # ----------------------------------------------------

        jobs.sort(

            key=lambda job: job["id"],

            reverse=True

        )


        # ----------------------------------------------------
        # SAVE CACHE
        # ----------------------------------------------------

        JOB_CACHE["jobs"] = jobs

        JOB_CACHE["timestamp"] = current_time


        print(
            f"Loaded {len(jobs)} jobs successfully"
        )


        return {

            "success": True,

            "count": len(jobs),

            "jobs": jobs,

            "cached": False

        }


    except Exception as e:

        print(
            "Get jobs API error:",
            str(e)
        )


        raise HTTPException(

            status_code=500,

            detail=(
                f"Could not fetch jobs: {str(e)}"
            )

        )


# ============================================================
# GET SINGLE JOB
# IMPORTANT: KEEP THIS AFTER FIXED ROUTES
# ============================================================

@router.get("/{job_id}")
def get_job(job_id: int):

    try:

        if job_id < 0:

            raise HTTPException(

                status_code=400,

                detail="Invalid job ID"

            )


        job = contract.functions.getJob(
            job_id
        ).call()


        formatted_job = format_job(
            job
        )


        zero_address = (
            "0x0000000000000000000000000000000000000000"
        )


        if formatted_job["client"] == zero_address:

            raise HTTPException(

                status_code=404,

                detail="Job not found"

            )


        return {

            "success": True,

            "job": formatted_job

        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "Get job API error:",
            str(e)
        )


        raise HTTPException(

            status_code=500,

            detail=(
                f"Could not fetch job: {str(e)}"
            )

        )