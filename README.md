# Trustlance

Trustlance is an AI-verified decentralized freelance marketplace built around Polygon Amoy escrow, IPFS evidence, an off-chain AI oracle, and on-chain reputation.

## Product Flow

```text
Client creates and funds a job with MetaMask
	|
Client assigns a freelancer wallet with MetaMask
	|
Freelancer uploads work to IPFS
	|
Freelancer submits the returned CID with MetaMask
	|
Oracle downloads the evidence and runs the matching AI checker
	|
Oracle records the score on-chain
	|
Escrow releases or holds funds according to the threshold
```

## Features

- Separate Client and Freelancer portals.
- MetaMask transactions on Polygon Amoy, chain ID `80002`.
- Client job creation, escrow funding, and freelancer assignment.
- Freelancer text, code, image, and audio submissions.
- Upload-only IPFS endpoint followed by a freelancer-signed `submitWork` transaction.
- AI verification for relevance, duplication, code, image, and audio submissions.
- Automatic escrow release or hold based on the on-chain threshold.
- Reputation data and NFT-backed completion history.
- Live marketplace refresh with RPC-friendly caching.

## Project Structure

```text
frontend/     React + Vite application
backend/      FastAPI API, IPFS integration, AI pipeline, and oracle service
blockchain/   Hardhat project, Solidity contracts, and deployed artifacts
smart_contract/ Solidity source references
```

## Requirements

- Python 3.11+ recommended
- Node.js 18+
- MetaMask configured for Polygon Amoy
- A funded Polygon Amoy wallet for the selected portal role
- Pinata credentials and Polygon RPC configuration in `blockchain/.env`

## Configuration

Create or update `blockchain/.env` with local secrets. Do not commit this file:

```env
RPC_URL=https://polygon-amoy.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
PRIVATE_KEY=YOUR_CLIENT_PRIVATE_KEY
FREELANCER_PRIVATE_KEY=YOUR_FREELANCER_PRIVATE_KEY
PINATA_API_KEY=YOUR_PINATA_API_KEY
PINATA_API_SECRET=YOUR_PINATA_API_SECRET
REPUTATION_NFT_ADDRESS=YOUR_REPUTATION_NFT_ADDRESS
```

The browser never receives private keys. User-initiated client and freelancer transactions are signed by MetaMask.

## Run the Application

### Backend

From the repository root:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

API documentation is available at `http://127.0.0.1:8000/docs`.

### Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://127.0.0.1:5173`.

Optional frontend configuration:

```env
VITE_API_URL=http://127.0.0.1:8000
```

### Oracle Service

Open a third terminal and keep it running for automatic AI verification:

```powershell
.\venv\Scripts\Activate.ps1
python -m backend.oracle.oracle_service
```

Run only one oracle service instance at a time.

## Smart Contracts

The frontend uses the existing deployed escrow contract and Hardhat artifact ABI. It does not deploy contracts at runtime.

- Network: Polygon Amoy
- Chain ID: `80002`
- Escrow: configured in `frontend/src/services/web3.js`
- Explorer: https://amoy.polygonscan.com/

## Verification

```powershell
cd frontend
npm run build
```

```powershell
cd ..
python -m py_compile backend\app.py backend\api\routes\jobs.py backend\api\routes\submissions.py backend\oracle\oracle_service.py
```

## Security Notes

- Never commit `blockchain/.env`, private keys, API keys, or secrets.
- Use separate MetaMask accounts for client and freelancer testing.
- The freelancer account must match the wallet assigned to the selected job.
- The oracle service must remain online for submitted jobs to move to Held or Released.
