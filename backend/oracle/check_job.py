import json
import os
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3


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
# CONTRACT
# ============================================================

ESCROW_ADDRESS = "0x9AF814D18DD67B09CceA594d54f625fd63D0B870"


# ============================================================
# JOB TO CHECK
# ============================================================

JOB_ID_TO_CHECK = 50


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(ENV_PATH)

RPC_URL = os.getenv("RPC_URL")

if not RPC_URL:
    raise ValueError("RPC_URL missing from blockchain/.env")


# ============================================================
# LOAD ABI
# ============================================================

with open(ARTIFACT_PATH, "r", encoding="utf-8") as f:
    ABI = json.load(f)["abi"]


# ============================================================
# CONNECT
# ============================================================

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise RuntimeError("Could not connect to Polygon Amoy")


contract = w3.eth.contract(
    address=Web3.to_checksum_address(ESCROW_ADDRESS),
    abi=ABI
)


# ============================================================
# GET JOB
# ============================================================

job = contract.functions.getJob(
    JOB_ID_TO_CHECK
).call()


# ============================================================
# DISPLAY JOB
# ============================================================

print()
print("=" * 50)
print(f"JOB {JOB_ID_TO_CHECK} — CURRENT ON-CHAIN STATE")
print("=" * 50)

print("Job ID:         ", job[0])
print("Client:         ", job[1])
print("Freelancer:     ", job[2])
print("Amount:         ", w3.from_wei(job[3], "ether"), "POL")
print("Threshold:      ", job[4])
print("Title:          ", job[5])
print("IPFS CID:       ", job[6])
print("Submission Type:", job[7])
print("AI Score:       ", job[8])
print("Status:         ", job[9])