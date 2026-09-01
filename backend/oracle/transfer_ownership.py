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
PRIVATE_KEY = os.getenv("PRIVATE_KEY")  # must be the CURRENT owner's key -- your oracle/client wallet

REPUTATION_ADDRESS = "0x6CB2C5aAE2E5b516Fa60DB761199C747cbE9dD06"

ESCROW_ADDRESS = "0x9AF814D18DD67B09CceA594d54f625fd63D0B870"

ARTIFACT_PATH = BLOCKCHAIN_DIR / "artifacts" / "contracts" / "ReputationNFT.sol" / "ReputationNFT.json"

with open(ARTIFACT_PATH, "r", encoding="utf-8") as f:
    ABI = json.load(f)["abi"]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)

contract = w3.eth.contract(address=Web3.to_checksum_address(REPUTATION_ADDRESS), abi=ABI)

current_owner = contract.functions.owner().call()
print("Current owner:", current_owner)
print("Transferring ownership to FreelanceEscrow:", ESCROW_ADDRESS)

nonce = w3.eth.get_transaction_count(account.address, "pending")
gas_price = w3.eth.gas_price

transaction = contract.functions.transferOwnership(
    Web3.to_checksum_address(ESCROW_ADDRESS)
).build_transaction({
    "from": account.address,
    "nonce": nonce,
    "gas": 100000,
    "gasPrice": gas_price,
    "chainId": w3.eth.chain_id,
})

signed = account.sign_transaction(transaction)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print("Transaction:", tx_hash.hex())

receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print("Confirmed in block:", receipt.blockNumber)

new_owner = contract.functions.owner().call()
print()
print("New owner is now:", new_owner)
if new_owner.lower() == ESCROW_ADDRESS.lower():
    print("✅ Ownership successfully transferred to FreelanceEscrow.")
else:
    print("❌ Something went wrong -- owner did not change as expected.")