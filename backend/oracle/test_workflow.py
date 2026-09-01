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
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(ENV_PATH)

RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")


# ============================================================
# DEPLOYED CONTRACT
# ============================================================

ESCROW_ADDRESS = "0x9AF814D18DD67B09CceA594d54f625fd63D0B870"


# ============================================================
# FREELANCER ADDRESS
# ============================================================
#
# For this first test, use another wallet address.
#
# IMPORTANT:
# Do NOT put a private key here.
#
# Replace this address with the wallet that will act
# as the freelancer.
#

FREELANCER_ADDRESS = "0xaEBe5A9fba82dd863628EdF77d0C49533C797466"


# ============================================================
# TEST JOB
# ============================================================

JOB_ID = 50

JOB_TITLE = "Record a clear professional voice explanation of how blockchain-based escrow protects both clients and freelancers during a payment dispute. Explain how funds are securely held until the agreed work is verified."

AI_THRESHOLD = 20

PAYMENT_POL = 0.001


# ============================================================
# LOAD ABI
# ============================================================

with open(ARTIFACT_PATH, "r", encoding="utf-8") as file:
    artifact = __import__("json").load(file)

ABI = artifact["abi"]


# ============================================================
# CONNECT
# ============================================================

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise Exception("Could not connect to Polygon Amoy")


account = w3.eth.account.from_key(PRIVATE_KEY)

print("=" * 60)
print("TRUSTLANCE TEST WORKFLOW")
print("=" * 60)

print("Client:", account.address)

print("Network:", w3.eth.chain_id)

print("Escrow:", ESCROW_ADDRESS)


# ============================================================
# CONTRACT
# ============================================================

contract = w3.eth.contract(
    address=Web3.to_checksum_address(ESCROW_ADDRESS),
    abi=ABI
)


# ============================================================
# HELPER: SEND TRANSACTION
# ============================================================

def send_transaction(function, value=0):

    nonce = w3.eth.get_transaction_count(
        account.address,
        "pending"
    )

    gas_price = w3.eth.gas_price

    # First estimate gas.
    # This often exposes the contract revert reason before sending.
    try:
        gas_estimate = function.estimate_gas({
            "from": account.address,
            "value": value
        })

        print("Estimated gas:", gas_estimate)

    except Exception as e:
        raise Exception(
            f"Transaction simulation/gas estimation failed:\n{e}"
        )

    transaction = function.build_transaction({
        "from": account.address,
        "value": value,
        "nonce": nonce,
        "gas": gas_estimate + 50000,
        "gasPrice": gas_price,
        "chainId": w3.eth.chain_id
    })

    signed = account.sign_transaction(transaction)

    tx_hash = w3.eth.send_raw_transaction(
        signed.raw_transaction
    )

    print("Transaction:", tx_hash.hex())

    receipt = w3.eth.wait_for_transaction_receipt(
        tx_hash
    )

    print("Receipt status:", receipt.status)
    print("Confirmed in block:", receipt.blockNumber)

    if receipt.status != 1:
        raise Exception(
            f"Transaction failed on blockchain:\n{tx_hash.hex()}"
        )

    return receipt


# ============================================================
# STEP 1
# CREATE JOB
# ============================================================

print()
print("=" * 60)
print("STEP 1: CREATE JOB")
print("=" * 60)

existing_job = contract.functions.getJob(JOB_ID).call()

existing_client = existing_job[1]

if existing_client != "0x0000000000000000000000000000000000000000":

    print("Job already exists.")

else:

    payment = w3.to_wei(
        PAYMENT_POL,
        "ether"
    )

    send_transaction(
        contract.functions.createJob(
            JOB_ID,
            JOB_TITLE,
            AI_THRESHOLD
        ),
        value=payment
    )

    print("Job created successfully.")


# ============================================================
# STEP 2
# ASSIGN FREELANCER
# ============================================================

print()
print("=" * 60)
print("STEP 2: ASSIGN FREELANCER")
print("=" * 60)

if FREELANCER_ADDRESS == "0xYOUR_FREELANCER_ADDRESS":

    raise Exception(
        "\nReplace FREELANCER_ADDRESS in test_workflow.py "
        "with the actual freelancer wallet address."
    )


freelancer = Web3.to_checksum_address(
    FREELANCER_ADDRESS
)


job = contract.functions.getJob(JOB_ID).call()

current_freelancer = job[2]

if current_freelancer == "0x0000000000000000000000000000000000000000":

    send_transaction(
        contract.functions.assignFreelancer(
            JOB_ID,
            freelancer
        )
    )

    print("Freelancer assigned.")

else:

    print(
        "Freelancer already assigned:",
        current_freelancer
    )


# ============================================================
# STEP 3
# DISPLAY JOB
# ============================================================

print()
print("=" * 60)
print("CURRENT JOB")
print("=" * 60)

job = contract.functions.getJob(JOB_ID).call()

print("Job ID:", job[0])
print("Client:", job[1])
print("Freelancer:", job[2])
print("Amount:", w3.from_wei(job[3], "ether"), "POL")
print("Threshold:", job[4])
print("Title:", job[5])
print("IPFS CID:", job[6])
print("AI Score:", job[7])
print("Status:", job[8])

print()
print("=" * 60)
print("NEXT STEP")
print("=" * 60)

print(
    "The freelancer must now call submitWork()."
)

print(
    "After submitWork(), the job status should become 2 (Submitted)."
)