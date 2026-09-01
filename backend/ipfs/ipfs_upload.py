import os
from pathlib import Path

from dotenv import load_dotenv
import requests


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_PATH = PROJECT_ROOT / "blockchain" / ".env"


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(ENV_PATH)

API_KEY = os.getenv("PINATA_API_KEY")
API_SECRET = os.getenv("PINATA_API_SECRET")


if not API_KEY or not API_SECRET:
    raise ValueError(
        "PINATA_API_KEY or PINATA_API_SECRET missing"
    )


# ============================================================
# IPFS UPLOAD
# ============================================================

def upload_to_ipfs(file_path):
    """
    Upload any file type to IPFS.

    Supported examples:
    - .txt
    - .py
    - .js
    - .jpg
    - .png
    - .mp3
    - .wav

    Returns:
        IPFS CID as a string.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"

    headers = {
        "pinata_api_key": API_KEY,
        "pinata_secret_api_key": API_SECRET
    }

    with open(file_path, "rb") as file:

        response = requests.post(
            url,
            headers=headers,
            files={
                "file": (
                    file_path.name,
                    file
                )
            },
            timeout=60
        )

    response.raise_for_status()

    data = response.json()

    return data["IpfsHash"]


# ============================================================
# DOWNLOAD TEXT FROM IPFS
# ============================================================

def download_from_ipfs(cid: str) -> str:
    """
    Download text content from IPFS.

    Use this for:
    - text submissions
    - code submissions that should be read as text

    Returns:
        File content as a string.
    """

    cid = cid.strip()

    if not cid:
        raise ValueError("IPFS CID cannot be empty")

    url = f"https://gateway.pinata.cloud/ipfs/{cid}"

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    return response.text


# ============================================================
# DOWNLOAD ANY FILE FROM IPFS
# ============================================================

def download_file_from_ipfs(
    cid: str,
    destination_dir,
    filename: str
) -> Path:
    """
    Download any file from IPFS and save it locally.

    Useful for:
    - images
    - audio
    - other binary files

    Parameters:
        cid:
            IPFS CID.

        destination_dir:
            Folder where the downloaded file will be stored.

        filename:
            Local filename to use.

    Returns:
        Path to the downloaded file.
    """

    cid = cid.strip()

    if not cid:
        raise ValueError("IPFS CID cannot be empty")

    destination_dir = Path(destination_dir)

    destination_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    destination_path = destination_dir / filename

    url = f"https://gateway.pinata.cloud/ipfs/{cid}"

    response = requests.get(
        url,
        stream=True,
        timeout=60
    )

    response.raise_for_status()

    with open(destination_path, "wb") as file:

        for chunk in response.iter_content(
            chunk_size=8192
        ):
            if chunk:
                file.write(chunk)

    return destination_path


# ============================================================
# GET IPFS GATEWAY URL
# ============================================================

def get_ipfs_url(cid: str) -> str:
    """
    Return the public Pinata gateway URL
    for an IPFS CID.
    """

    cid = cid.strip()

    if not cid:
        raise ValueError("IPFS CID cannot be empty")

    return f"https://gateway.pinata.cloud/ipfs/{cid}"


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    TEST_FILE = (
        PROJECT_ROOT
        / "backend"
        / "test_data"
        / "test_work.txt"
    )

    # Create a test file if it doesn't exist
    if not TEST_FILE.exists():

        TEST_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        TEST_FILE.write_text(
            "Trustlance IPFS integration test work.",
            encoding="utf-8"
        )

    print("=" * 60)
    print("TRUSTLANCE IPFS TEST")
    print("=" * 60)

    print()
    print("Uploading:")
    print(TEST_FILE)

    cid = upload_to_ipfs(TEST_FILE)

    print()
    print("UPLOAD SUCCESS")
    print("CID:", cid)

    print()
    print("Gateway:")
    print(get_ipfs_url(cid))

    # Test text download
    print()
    print("Downloading as text...")

    content = download_from_ipfs(cid)

    print("Content:")
    print(content)

    # Test file download
    print()
    print("Downloading as file...")

    DOWNLOAD_DIR = (
        PROJECT_ROOT
        / "backend"
        / "downloads"
    )

    downloaded_file = download_file_from_ipfs(
        cid=cid,
        destination_dir=DOWNLOAD_DIR,
        filename="ipfs_test_download.txt"
    )

    print("Downloaded file:")
    print(downloaded_file)

    print()
    print("=" * 60)
    print("IPFS TEST COMPLETE")
    print("=" * 60)