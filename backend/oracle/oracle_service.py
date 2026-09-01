import time
import sys
import json
from pathlib import Path

from web3 import Web3

# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================
# ORACLE DIRECTORY AND STATE FILE
# ============================================================

ORACLE_DIR = Path(__file__).resolve().parent
STATE_FILE = ORACLE_DIR / "oracle_state.json"

# ============================================================
# IMPORT AI ORACLE PIPELINE
# ============================================================

from backend.ai.ai_oracle_pipeline import (
    get_job_details,
    run_ai_verification,
)

# ============================================================
# IMPORT BLOCKCHAIN CONNECTION
# ============================================================

from backend.oracle.oracle_bridge import (
    get_web3,
    load_contract_abi,
    ESCROW_ADDRESS,
)

# ============================================================
# SETTINGS
# ============================================================

CHECK_INTERVAL = 5

# Maximum blocks queried in one RPC request.
# Keep this small for public Polygon Amoy RPC endpoints.
MAX_BLOCK_RANGE = 5

# Smallest batch size allowed when retrying.
MIN_BLOCK_RANGE = 1

# Number of retries for a failed RPC request.
MAX_QUERY_RETRIES = 3

# Delay between RPC retries.
QUERY_RETRY_DELAY = 2

# ============================================================
# LOAD ORACLE STATE
# ============================================================

def load_oracle_state():
    default_state = {
        "processed_jobs": [],
        "failed_jobs": [],
        "last_processed_block": 0,
    }

    if not STATE_FILE.exists():
        return default_state

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        if not isinstance(state, dict):
            return default_state

        if "processed_jobs" not in state:
            state["processed_jobs"] = []

        if "failed_jobs" not in state:
            state["failed_jobs"] = []

        if "last_processed_block" not in state:
            state["last_processed_block"] = 0

        return state

    except Exception as e:
        print()
        print("WARNING: Could not load oracle state.")
        print(f"Reason: {e}")
        return default_state


# ============================================================
# SAVE ORACLE STATE
# ============================================================

def save_oracle_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print()
        print("WARNING: Could not save oracle state.")
        print(f"Reason: {e}")


# ============================================================
# UPDATE STATE
# ============================================================

def update_state(state, processed_jobs, failed_jobs, last_processed_block=None):
    state["processed_jobs"] = sorted(list(processed_jobs))
    state["failed_jobs"] = sorted(list(failed_jobs))

    if last_processed_block is not None:
        state["last_processed_block"] = int(last_processed_block)

    save_oracle_state(state)


# ============================================================
# PROCESS ONE JOB
# ============================================================

def process_job(job_id, processed_jobs, failed_jobs, state):
    job_id = int(job_id)

    # --------------------------------------------------------
    # SKIP ALREADY PROCESSED
    # --------------------------------------------------------
    if job_id in processed_jobs:
        print(f"Job {job_id} already processed. Skipping.")
        return True

    # --------------------------------------------------------
    # SKIP PREVIOUSLY FAILED
    # --------------------------------------------------------
    if job_id in failed_jobs:
        print(f"Job {job_id} previously failed. Skipping.")
        return False

    # --------------------------------------------------------
    # GET JOB DETAILS
    # --------------------------------------------------------
    try:
        details = get_job_details(job_id)
    except Exception as e:
        print()
        print(f"Could not fetch job {job_id}.")
        print(f"Reason: {e}")
        return False

    if not details:
        print(f"Job {job_id} does not exist.")
        return False

    # --------------------------------------------------------
    # ONLY PROCESS SUBMITTED JOBS
    # --------------------------------------------------------
    status = details.get("status")
    if status != 2:
        print(f"Job {job_id} is not in Submitted status.")
        print(f"Current status: {status}")
        return False

    # ========================================================
    # NEW SUBMISSION
    # ========================================================
    print()
    print("=" * 60)
    print(f"NEW SUBMISSION DETECTED: JOB {job_id}")
    print("Submission type:", details.get("submission_type"))
    print("Running AI verification...")
    print("=" * 60)

    # ========================================================
    # RUN AI VERIFICATION
    # ========================================================
    try:
        result = run_ai_verification(job_id=job_id)

    # ========================================================
    # JOB FAILED
    # ========================================================
    except Exception as e:
        failed_jobs.add(job_id)
        update_state(state, processed_jobs, failed_jobs)

        print()
        print("=" * 60)
        print(f"JOB {job_id} FAILED")
        print("=" * 60)
        print(f"Reason: {e}")
        print("Job saved as FAILED.")
        return False

    # ========================================================
    # JOB SUCCESSFUL
    # ========================================================
    processed_jobs.add(job_id)

    if job_id in failed_jobs:
        failed_jobs.remove(job_id)

    # Save immediately
    update_state(state, processed_jobs, failed_jobs)

    # ========================================================
    # SUCCESS MESSAGE
    # ========================================================
    print()
    print("=" * 60)
    print(f"JOB {job_id} PROCESSED SUCCESSFULLY")
    print(f"Final score: {result['ai_result']['final_score']}")
    print("=" * 60)

    return True


# ============================================================
# GET CONTRACT
# ============================================================

def get_contract():
    w3 = get_web3()

    if not w3.is_connected():
        raise Exception("Could not connect to blockchain RPC.")

    abi = load_contract_abi()
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(ESCROW_ADDRESS),
        abi=abi,
    )

    return w3, contract


# ============================================================
# GET WORK SUBMITTED EVENTS SAFELY
# ============================================================

def get_work_submitted_events(
    w3,
    contract,
    start_block,
    end_block
):

    all_events = []

    current_block = int(start_block)
    end_block = int(end_block)

    batch_size = MAX_BLOCK_RANGE


    # ========================================================
    # LOOP THROUGH BLOCKS
    # ========================================================

    while current_block <= end_block:

        batch_end = min(
            current_block + batch_size - 1,
            end_block
        )

        print(
            f"Checking blocks "
            f"{current_block} to {batch_end}..."
        )


        # ====================================================
        # QUERY WITH RETRIES
        # ====================================================

        success = False

        for attempt in range(
            1,
            MAX_QUERY_RETRIES + 1
        ):

            try:

                # --------------------------------------------
                # USE WEB3 CONTRACT EVENT QUERY
                # --------------------------------------------

                events = contract.events.WorkSubmitted().get_logs(
                    from_block=current_block,
                    to_block=batch_end
                )


                # --------------------------------------------
                # ADD EVENTS
                # --------------------------------------------

                all_events.extend(events)

                success = True

                break


            except Exception as e:

                print()

                print(
                    f"EVENT QUERY FAILED "
                    f"(Attempt {attempt}/{MAX_QUERY_RETRIES})"
                )

                print(
                    f"Blocks: "
                    f"{current_block} to {batch_end}"
                )

                print(
                    f"Reason: {e}"
                )


                if attempt < MAX_QUERY_RETRIES:

                    print(
                        f"Retrying in "
                        f"{QUERY_RETRY_DELAY} seconds..."
                    )

                    time.sleep(
                        QUERY_RETRY_DELAY
                    )


        # ====================================================
        # QUERY FAILED
        # ====================================================

        if not success:

            # Reduce batch size

            if batch_size > MIN_BLOCK_RANGE:

                new_batch_size = max(
                    MIN_BLOCK_RANGE,
                    batch_size // 2
                )

                print()

                print(
                    f"Reducing block batch size: "
                    f"{batch_size} -> {new_batch_size}"
                )

                batch_size = new_batch_size

                # Retry same block range

                continue


            # Even minimum range failed

            raise Exception(
                f"Event query failed for blocks "
                f"{current_block} to {batch_end}"
            )


        # ====================================================
        # MOVE TO NEXT BATCH
        # ====================================================

        current_block = batch_end + 1


        # ====================================================
        # RESTORE BATCH SIZE
        # ====================================================

        if batch_size < MAX_BLOCK_RANGE:

            batch_size = min(
                MAX_BLOCK_RANGE,
                batch_size * 2
            )
    return all_events
   
# ============================================================
# AUTOMATIC EVENT-BASED ORACLE SERVICE
# ============================================================

def run_oracle_service():
    # --------------------------------------------------------
    # LOAD PERSISTENT STATE
    # --------------------------------------------------------
    state = load_oracle_state()
    processed_jobs = {int(job_id) for job_id in state["processed_jobs"]}
    failed_jobs = {int(job_id) for job_id in state["failed_jobs"]}

    # ========================================================
    # CONNECT TO BLOCKCHAIN
    # ========================================================
    print()
    print("=" * 60)
    print("TRUSTLANCE AUTOMATIC ORACLE SERVICE")
    print("=" * 60)
    print()
    print("Connecting to Polygon Amoy...")

    try:
        w3, contract = get_contract()
        print("Connected successfully.")
        print(f"Chain ID: {w3.eth.chain_id}")
        print(f"Escrow contract: {contract.address}")
    except Exception as e:
        print()
        print("=" * 60)
        print("BLOCKCHAIN CONNECTION FAILED")
        print("=" * 60)
        print(f"Reason: {e}")
        return

    # ========================================================
    # DETERMINE START BLOCK
    # ========================================================
    current_block = w3.eth.block_number
    last_processed_block = int(state.get("last_processed_block", 0))

    # --------------------------------------------------------
    # FIRST RUN
    # --------------------------------------------------------
    if last_processed_block == 0:
        last_processed_block = current_block
        state["last_processed_block"] = last_processed_block
        save_oracle_state(state)
        print()
        print("Starting event listener from current block:")
        print(last_processed_block)

    # --------------------------------------------------------
    # RESTART
    # --------------------------------------------------------
    
    else:
        # Start from the current blockchain block on restart
        # This avoids scanning a large number of old blocks.
        last_processed_block = current_block
        state["last_processed_block"] = last_processed_block
        save_oracle_state(state)

        print()
        print("Restarting event listener from current block:")
        print(last_processed_block)

    # ========================================================
    # START MESSAGE
    # ========================================================
    print()
    print(f"Previously processed jobs: {len(processed_jobs)}")
    print(f"Previously failed jobs: {len(failed_jobs)}")
    print()
    print("Listening for WorkSubmitted events...")
    print()

    # ========================================================
    # MAIN EVENT LOOP
    # ========================================================
    while True:
        try:
            # ------------------------------------------------
            # CHECK CONNECTION
            # ------------------------------------------------
            if not w3.is_connected():
                print()
                print("Blockchain connection lost.")
                print("Reconnecting...")
                w3, contract = get_contract()
                time.sleep(CHECK_INTERVAL)
                continue

            # ------------------------------------------------
            # GET LATEST BLOCK
            # ------------------------------------------------
            latest_block = w3.eth.block_number

            # ------------------------------------------------
            # NO NEW BLOCKS
            # ------------------------------------------------
            if latest_block <= last_processed_block:
                time.sleep(CHECK_INTERVAL)
                continue

            # ------------------------------------------------
            # BLOCK RANGE TO PROCESS
            # ------------------------------------------------
            from_block = last_processed_block + 1
            to_block = latest_block

            print()
            print("=" * 60)
            print(f"NEW BLOCKS DETECTED: {from_block} to {to_block}")
            print("=" * 60)

            # =================================================
            # GET WorkSubmitted EVENTS SAFELY
            # =================================================
            try:
                events = get_work_submitted_events(
                    w3=w3,
                    contract=contract,
                    start_block=from_block,
                    end_block=to_block,
                )
            except Exception as e:
                print()
                print("=" * 60)
                print("EVENT QUERY FAILED")
                print("=" * 60)
                print(f"Blocks: {from_block} to {to_block}")
                print(f"Reason: {e}")
                print()
                print("IMPORTANT: These blocks were NOT marked as processed.")
                print(f"Retrying in {CHECK_INTERVAL} seconds...")
                time.sleep(CHECK_INTERVAL)
                continue

            # =================================================
            # PROCESS EVENTS
            # =================================================
            if len(events) == 0:
                print()
                print("No WorkSubmitted events found.")
            else:
                print()
                print(f"Found {len(events)} WorkSubmitted event(s).")

            for event in events:
                job_id = int(event["args"]["jobId"])

                print()
                print("=" * 60)
                print("WORK SUBMITTED EVENT DETECTED")
                print("=" * 60)
                print(f"Job ID: {job_id}")

                # --------------------------------------------
                # IPFS CID
                # --------------------------------------------
                try:
                    ipfs_cid = event["args"]["ipfsCID"]
                    print(f"IPFS CID: {ipfs_cid}")
                except Exception:
                    print("IPFS CID: Not available in event.")

                # --------------------------------------------
                # PROCESS JOB
                # --------------------------------------------
                process_job(
                    job_id=job_id,
                    processed_jobs=processed_jobs,
                    failed_jobs=failed_jobs,
                    state=state,
                )

            # =================================================
            # UPDATE LAST PROCESSED BLOCK
            # =================================================
            # IMPORTANT:
            # We only reach here if ALL event queries completed successfully.
            last_processed_block = latest_block
            update_state(state, processed_jobs, failed_jobs, last_processed_block)

            print()
            print(f"Block progress saved: {last_processed_block}")

            # =================================================
            # WAIT
            # =================================================
            time.sleep(CHECK_INTERVAL)

        # ====================================================
        # STOP SERVICE
        # ====================================================
        except KeyboardInterrupt:
            update_state(state, processed_jobs, failed_jobs, last_processed_block)

            print()
            print("=" * 60)
            print("ORACLE SERVICE STOPPED")
            print("=" * 60)
            print()
            print(f"Processed jobs saved: {len(processed_jobs)}")
            print(f"Failed jobs saved: {len(failed_jobs)}")
            print(f"Last processed block: {last_processed_block}")
            break

        # ====================================================
        # SERVICE ERROR
        # ====================================================
        except Exception as e:
            print()
            print("=" * 60)
            print("ORACLE SERVICE ERROR")
            print("=" * 60)
            print(f"Reason: {e}")
            print()
            print(f"Retrying in {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)


# ============================================================
# START SERVICE
# ============================================================

if __name__ == "__main__":
    run_oracle_service()
