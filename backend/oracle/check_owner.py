import os
import json
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLOCKCHAIN_DIR = PROJECT_ROOT / "blockchain"
ENV_PATH = BLOCKCHAIN_DIR / ".env"

load_dotenv(ENV_PATH)
RPC_URL = os.getenv("RPC_URL")

REPUTATION_ADDRESS = "0x6CB2C5aAE2E5b516Fa60DB761199C747cbE9dD06"
ESCROW_ADDRESS = "0x9AF814D18DD67B09CceA594d54f625fd63D0B870"

ARTIFACT_PATH = BLOCKCHAIN_DIR / "artifacts" / "contracts" / "ReputationNFT.sol" / "ReputationNFT.json"

with open(ARTIFACT_PATH, "r", encoding="utf-8") as f:
    ABI = json.load(f)["abi"]

w3 = Web3(Web3.HTTPProvider(RPC_URL))

contract = w3.eth.contract(address=Web3.to_checksum_address(REPUTATION_ADDRESS), abi=ABI)

current_owner = contract.functions.owner().call()

print("ReputationNFT owner is:", current_owner)
print("FreelanceEscrow address is:", ESCROW_ADDRESS)
print()
if current_owner.lower() == ESCROW_ADDRESS.lower():
    print("✅ Ownership is correctly set to the Escrow contract.")
else:
    print("❌ MISMATCH — this confirms the ownership transfer was never done.")
    print("   FreelanceEscrow cannot call mintReputation() until you fix this.")