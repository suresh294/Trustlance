import os
import json
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3

import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2])
)

from backend.ipfs.ipfs_upload import upload_to_ipfs


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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
FREELANCER_PRIVATE_KEY = os.getenv("FREELANCER_PRIVATE_KEY")


if not RPC_URL:
    raise ValueError("RPC_URL missing from blockchain/.env")

if not FREELANCER_PRIVATE_KEY:
    raise ValueError(
        "FREELANCER_PRIVATE_KEY missing from blockchain/.env"
    )


# ============================================================
# DEPLOYED ESCROW CONTRACT
# ============================================================

# KEEP USING THE CURRENT WORKING CONTRACT
ESCROW_ADDRESS = "0x9AF814D18DD67B09CceA594d54f625fd63D0B870"


# ============================================================
# SUBMISSION CONFIGURATION
# ============================================================

JOB_ID = 42

# Allowed:
# text
# code
# image
# audio
SUBMISSION_TYPE = "text"


# ============================================================
# WORK FILE
# ============================================================

# CHANGE THIS FILE DEPENDING ON SUBMISSION TYPE

WORK_FILE = (
    PROJECT_ROOT
    / "backend"
    / "test_data"
    / "s.txt"
)


# ============================================================
# VALIDATE SUBMISSION TYPE
# ============================================================

VALID_SUBMISSION_TYPES = {
    "text",
    "code",
    "image",
    "audio"
}

SUBMISSION_TYPE = SUBMISSION_TYPE.lower().strip()

if SUBMISSION_TYPE not in VALID_SUBMISSION_TYPES:
    raise ValueError(
        f"Invalid submission type: {SUBMISSION_TYPE}\n"
        f"Allowed types: {', '.join(sorted(VALID_SUBMISSION_TYPES))}"
    )


# ============================================================
# LOAD ABI
# ============================================================

if not ARTIFACT_PATH.exists():
    raise FileNotFoundError(
        f"Contract artifact not found:\n{ARTIFACT_PATH}"
    )

with open(ARTIFACT_PATH, "r", encoding="utf-8") as f:
    ABI = json.load(f)["abi"]


# ============================================================
# CONNECT TO POLYGON AMOY
# ============================================================

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise Exception("Could not connect to Polygon Amoy")


# ============================================================
# FREELANCER ACCOUNT
# ============================================================

freelancer_account = w3.eth.account.from_key(
    FREELANCER_PRIVATE_KEY
)


# ============================================================
# DISPLAY INFO
# ============================================================

print("=" * 60)
print("TRUSTLANCE UNIVERSAL WORK SUBMISSION")
print("=" * 60)

print("Freelancer address:", freelancer_account.address)
print("Job ID:", JOB_ID)
print("Network Chain ID:", w3.eth.chain_id)
print("Submission type:", SUBMISSION_TYPE)


# ============================================================
# CONTRACT
# ============================================================

contract = w3.eth.contract(
    address=Web3.to_checksum_address(ESCROW_ADDRESS),
    abi=ABI
)


# ============================================================
# CHECK JOB
# ============================================================

print()
print("Checking job on blockchain...")

job = contract.functions.getJob(JOB_ID).call()

assigned_freelancer = job[2]
current_status = int(job[9])

print("Current job status:", current_status)
print("Assigned freelancer:", assigned_freelancer)


# ============================================================
# VERIFY FREELANCER
# ============================================================

if (
    freelancer_account.address.lower()
    != assigned_freelancer.lower()
):
    raise Exception(
        f"\nThis wallet is not the assigned freelancer.\n\n"
        f"Current wallet:\n{freelancer_account.address}\n\n"
        f"Assigned freelancer:\n{assigned_freelancer}"
    )


# ============================================================
# VERIFY JOB STATUS
# ============================================================

# 1 = Assigned
if current_status != 1:
    raise Exception(
        f"\nJob {JOB_ID} cannot accept a submission.\n"
        f"Expected status: 1 (Assigned)\n"
        f"Current status: {current_status}"
    )


# ============================================================
# VERIFY WORK FILE
# ============================================================

if not WORK_FILE.exists():
    raise FileNotFoundError(
        f"\nWork file not found:\n{WORK_FILE}"
    )

print()
print("Work file:")
print(WORK_FILE)


# ============================================================
# UPLOAD WORK TO IPFS
# ============================================================

print()
print("=" * 60)
print(f"UPLOADING {SUBMISSION_TYPE.upper()} SUBMISSION TO IPFS")
print("=" * 60)

ipfs_cid = upload_to_ipfs(WORK_FILE)

if not ipfs_cid:
    raise Exception("IPFS upload failed. No CID returned.")

print()
print("IPFS CID:")
print(ipfs_cid)

print()
print("IPFS Gateway:")
print(
    f"https://gateway.pinata.cloud/ipfs/{ipfs_cid}"
)


# ============================================================
# ESTIMATE GAS
# ============================================================

print()
print("Estimating gas...")

gas_estimate = contract.functions.submitWork(
    JOB_ID,
    ipfs_cid,
    SUBMISSION_TYPE
).estimate_gas({
    "from": freelancer_account.address
})

print("Estimated gas:", gas_estimate)


# ============================================================
# BUILD TRANSACTION
# ============================================================

print()
print("Building transaction...")

nonce = w3.eth.get_transaction_count(
    freelancer_account.address,
    "pending"
)

gas_price = w3.eth.gas_price

transaction = contract.functions.submitWork(
    JOB_ID,
    ipfs_cid,
    SUBMISSION_TYPE
).build_transaction({
    "from": freelancer_account.address,
    "nonce": nonce,
    "gas": gas_estimate + 10000,
    "gasPrice": gas_price,
    "chainId": w3.eth.chain_id,
})


# ============================================================
# SIGN TRANSACTION
# ============================================================

print("Signing transaction...")

signed = freelancer_account.sign_transaction(
    transaction
)


# ============================================================
# SEND TRANSACTION
# ============================================================

print("Sending transaction...")

tx_hash = w3.eth.send_raw_transaction(
    signed.raw_transaction
)

print()
print("Transaction Hash:")
print(tx_hash.hex())

print()
print("Waiting for blockchain confirmation...")


# ============================================================
# WAIT FOR CONFIRMATION
# ============================================================

receipt = w3.eth.wait_for_transaction_receipt(
    tx_hash
)

print()
print("Confirmed in block:", receipt.blockNumber)
print("Receipt status:", receipt.status)


if receipt.status != 1:
    raise Exception(
        f"submitWork transaction failed:\n{tx_hash.hex()}"
    )


# ============================================================
# VERIFY ON BLOCKCHAIN
# ============================================================

print()
print("Verifying submission on blockchain...")

job = contract.functions.getJob(JOB_ID).call()


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("=" * 60)
print("SUBMISSION RESULT")
print("=" * 60)

print("Job ID:", job[0])
print("Freelancer:", job[2])
print("Job Brief:", job[5])
print("IPFS CID:", job[6])
print("Submission Type:", job[7])
print("AI Score:", job[8])
print("Status:", job[9])


print()
print("Blockchain Transaction:")
print(
    f"https://amoy.polygonscan.com/tx/{tx_hash.hex()}"
)


print()
print("IPFS Submission:")
print(
    f"https://gateway.pinata.cloud/ipfs/{job[6]}"
)


# ============================================================
# SUCCESS CHECK
# ============================================================

# 2 = Submitted

if int(job[9]) == 2:

    print()
    print("=" * 60)
    print("SUCCESS")
    print("=" * 60)

    print(
        f"{SUBMISSION_TYPE.upper()} submission successfully stored "
        f"on blockchain."
    )

    print()
    print("The Universal AI Oracle Pipeline can now process:")
    print(f"Job ID: {JOB_ID}")
    print(f"Submission Type: {job[7]}")
    print(f"IPFS CID: {job[6]}")

else:

    print()
    print(
        f"WARNING: Expected status 2 (Submitted), "
        f"got {job[9]}"
    )
