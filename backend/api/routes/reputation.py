import os
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv
from web3 import Web3


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
    / "ReputationNFT.sol"
    / "ReputationNFT.json"
)


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(ENV_PATH)

RPC_URL = os.getenv("RPC_URL")

REPUTATION_ADDRESS = os.getenv("REPUTATION_NFT_ADDRESS")


if not RPC_URL:
    raise ValueError(
        "RPC_URL is missing from blockchain/.env"
    )


if not REPUTATION_ADDRESS:
    raise ValueError(
        "REPUTATION_NFT_ADDRESS is missing from blockchain/.env"
    )


# ============================================================
# CHECK ARTIFACT
# ============================================================

if not ARTIFACT_PATH.exists():
    raise FileNotFoundError(
        f"ReputationNFT artifact not found: {ARTIFACT_PATH}"
    )


# ============================================================
# BLOCKCHAIN CONNECTION
# ============================================================

w3 = Web3(
    Web3.HTTPProvider(
        RPC_URL,
        request_kwargs={
            "timeout": 20
        }
    )
)


# ============================================================
# LOAD CONTRACT ABI
# ============================================================

with open(
    ARTIFACT_PATH,
    "r",
    encoding="utf-8"
) as f:

    REPUTATION_ABI = json.load(f)["abi"]


# ============================================================
# CONTRACT INSTANCE
# ============================================================

reputation_contract = w3.eth.contract(
    address=Web3.to_checksum_address(
        REPUTATION_ADDRESS
    ),
    abi=REPUTATION_ABI
)


# ============================================================
# API STATUS
# ============================================================

@router.get("/status")
def reputation_status():

    try:

        return {
            "success": True,
            "message": "Reputation API is working",
            "blockchain_connected": w3.is_connected(),
            "chain_id": (
                w3.eth.chain_id
                if w3.is_connected()
                else None
            ),
            "contract_address": REPUTATION_ADDRESS
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e),
            "blockchain_connected": False
        }


# ============================================================
# GET FREELANCER REPUTATION
# ============================================================

@router.get("/{freelancer_address}")
def get_reputation(freelancer_address: str):

    try:

        # ----------------------------------------------------
        # CHECK BLOCKCHAIN CONNECTION
        # ----------------------------------------------------

        if not w3.is_connected():

            raise HTTPException(
                status_code=503,
                detail="Blockchain connection unavailable"
            )


        # ----------------------------------------------------
        # VALIDATE WALLET ADDRESS
        # ----------------------------------------------------

        if not Web3.is_address(
            freelancer_address
        ):

            raise HTTPException(
                status_code=400,
                detail="Invalid wallet address"
            )


        freelancer = Web3.to_checksum_address(
            freelancer_address
        )


        # ----------------------------------------------------
        # GET REPUTATION DATA
        # ----------------------------------------------------

        reputation = reputation_contract.functions.reputation(
            freelancer
        ).call()


        completed_jobs = int(reputation[0])

        total_ai_score = int(reputation[1])


        # ----------------------------------------------------
        # GET AVERAGE AI SCORE
        # ----------------------------------------------------

        average_score = int(
            reputation_contract.functions.getAverageScore(
                freelancer
            ).call()
        )


        # ----------------------------------------------------
        # GET NUMBER OF REPUTATION NFTs
        # ----------------------------------------------------

        nft_count = int(
            reputation_contract.functions.balanceOf(
                freelancer
            ).call()
        )


        # ----------------------------------------------------
        # RETURN RESPONSE
        # ----------------------------------------------------

        return {
            "success": True,

            "freelancer": freelancer,

            "nft_count": nft_count,

            "completed_jobs": completed_jobs,

            "total_ai_score": total_ai_score,

            "average_ai_score": average_score,

            "nft_type": (
                "Soulbound Reputation NFT"
            ),

            "transferable": False
        }


    except HTTPException:
        raise


    except Exception as e:

        print(
            "Reputation API error:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not fetch reputation: "
                f"{str(e)}"
            )
        )