from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pathlib import Path
import os
import json

from dotenv import load_dotenv
from web3 import Web3

from backend.ipfs.ipfs_upload import upload_to_ipfs


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

DOWNLOADS_DIR = PROJECT_ROOT / "backend" / "downloads"


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(ENV_PATH)

RPC_URL = os.getenv("RPC_URL")
FREELANCER_PRIVATE_KEY = os.getenv("FREELANCER_PRIVATE_KEY")

ESCROW_ADDRESS = "0x9AF814D18DD67B09CceA594d54f625fd63D0B870"


# ============================================================
# VALID SUBMISSION TYPES
# ============================================================

VALID_SUBMISSION_TYPES = {
    "text",
    "code",
    "image",
    "audio"
}


# ============================================================
# BLOCKCHAIN CONNECTION
# ============================================================

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise RuntimeError("Could not connect to Polygon Amoy")


# ============================================================
# LOAD ESCROW ABI
# ============================================================

with open(ARTIFACT_PATH, "r", encoding="utf-8") as f:
    ESCROW_ABI = json.load(f)["abi"]


contract = w3.eth.contract(
    address=Web3.to_checksum_address(ESCROW_ADDRESS),
    abi=ESCROW_ABI
)


# ============================================================
# SUBMIT WORK
# ============================================================

@router.post("/")
async def submit_submission(

    job_id: int = Form(...),

    submission_type: str = Form(...),

    file: UploadFile = File(...)

):

    try:

        # ----------------------------------------------------
        # VALIDATE TYPE
        # ----------------------------------------------------

        submission_type = submission_type.lower().strip()

        if submission_type not in VALID_SUBMISSION_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid submission type. "
                    "Allowed: text, code, image, audio"
                )
            )


        # ----------------------------------------------------
        # FREELANCER ACCOUNT
        # ----------------------------------------------------

        freelancer_account = w3.eth.account.from_key(
            FREELANCER_PRIVATE_KEY
        )


        # ----------------------------------------------------
        # CHECK JOB
        # ----------------------------------------------------

        job = contract.functions.getJob(job_id).call()

        assigned_freelancer = job[2]

        current_status = int(job[9])


        # ----------------------------------------------------
        # VERIFY FREELANCER
        # ----------------------------------------------------

        if (
            freelancer_account.address.lower()
            != assigned_freelancer.lower()
        ):
            raise HTTPException(
                status_code=403,
                detail="Configured wallet is not the assigned freelancer"
            )


        # ----------------------------------------------------
        # VERIFY JOB STATUS
        # ----------------------------------------------------

        if current_status != 1:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Job cannot accept submission. "
                    f"Current status: {current_status}"
                )
            )


        # ----------------------------------------------------
        # SAVE UPLOADED FILE TEMPORARILY
        # ----------------------------------------------------

        DOWNLOADS_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        safe_filename = Path(file.filename).name

        temp_file_path = (
            DOWNLOADS_DIR
            / f"job_{job_id}_{safe_filename}"
        )


        contents = await file.read()

        with open(temp_file_path, "wb") as f:
            f.write(contents)


        # ----------------------------------------------------
        # UPLOAD TO IPFS
        # ----------------------------------------------------

        ipfs_cid = upload_to_ipfs(
            temp_file_path
        )

        if not ipfs_cid:

            raise HTTPException(
                status_code=500,
                detail="IPFS upload failed"
            )


        # ----------------------------------------------------
        # ESTIMATE GAS
        # ----------------------------------------------------

        gas_estimate = contract.functions.submitWork(
            job_id,
            ipfs_cid,
            submission_type
        ).estimate_gas({

            "from": freelancer_account.address

        })


        # ----------------------------------------------------
        # BUILD TRANSACTION
        # ----------------------------------------------------

        nonce = w3.eth.get_transaction_count(
            freelancer_account.address,
            "pending"
        )

        transaction = contract.functions.submitWork(
            job_id,
            ipfs_cid,
            submission_type
        ).build_transaction({

            "from": freelancer_account.address,

            "nonce": nonce,

            "gas": gas_estimate + 10000,

            "gasPrice": w3.eth.gas_price,

            "chainId": w3.eth.chain_id

        })


        # ----------------------------------------------------
        # SIGN TRANSACTION
        # ----------------------------------------------------

        signed_transaction = (
            freelancer_account.sign_transaction(
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
                detail="Blockchain submission transaction failed"
            )


        # ----------------------------------------------------
        # SUCCESS RESPONSE
        # ----------------------------------------------------

        return {

            "success": True,

            "message": (
                "Submission successfully uploaded and "
                "recorded on blockchain"
            ),

            "job_id": job_id,

            "submission_type": submission_type,

            "ipfs_cid": ipfs_cid,

            "transaction_hash": tx_hash.hex(),

            "explorer_url": (
                f"https://amoy.polygonscan.com/tx/"
                f"{tx_hash.hex()}"
            ),

            "ipfs_url": (
                f"https://gateway.pinata.cloud/ipfs/"
                f"{ipfs_cid}"
            )

        }


    except HTTPException:
        raise


    except Exception as e:

        print("Submission API error:", str(e))

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )