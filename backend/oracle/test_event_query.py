import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web3 import Web3

from backend.oracle.oracle_bridge import (
    get_web3,
    load_contract_abi,
    ESCROW_ADDRESS,
)


print("=" * 60)
print("TRUSTLANCE EVENT QUERY TEST")
print("=" * 60)

w3 = get_web3()

print("Connected:", w3.is_connected())
print("Chain ID:", w3.eth.chain_id)

abi = load_contract_abi()

contract = w3.eth.contract(
    address=Web3.to_checksum_address(ESCROW_ADDRESS),
    abi=abi
)

latest_block = w3.eth.block_number

print("Latest block:", latest_block)

start_block = latest_block - 1

print()
print(
    f"Testing WorkSubmitted event query "
    f"from {start_block} to {latest_block}"
)

print()

try:

    events = contract.events.WorkSubmitted().get_logs(
        from_block=start_block,
        to_block=latest_block
    )

    print("SUCCESS")
    print("Events found:", len(events))

    for event in events:

        print(event["args"])

except Exception as e:

    print("FAILED")
    print("Error:", repr(e))