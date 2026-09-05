# Trustlance Frontend

The React + Vite frontend provides separate Client and Freelancer portals for the Trustlance marketplace. It reads jobs and verification results from the existing FastAPI API and uses MetaMask for user-initiated Polygon Amoy transactions.

## Run

From `Trustlance/frontend`:

```bash
npm install
npm run dev
```

The UI expects the existing backend at `http://127.0.0.1:8000` by default.

To use another backend URL:

```bash
# .env
VITE_API_URL=http://127.0.0.1:8000
```

## Backend endpoints used

- `GET /api/jobs/`
- `GET /api/jobs/status/test`
- `GET /api/jobs/{job_id}`
- `POST /api/submissions/upload`
- `GET /api/reputation/{freelancer_address}`

The legacy submission endpoint remains available for existing workflows but is not used by the MetaMask submission flow.

## Wallet behavior

The UI exposes separate Client and Freelancer portals and validates MetaMask on Polygon Amoy (`80002`). Client creation and freelancer assignment are signed by the active client account. Freelancer submission uploads evidence through the upload-only endpoint, then signs `submitWork(jobId, cid, submissionType)` directly with the assigned freelancer account.

The UI listens for MetaMask account and network changes. The freelancer account must match the wallet assigned to the selected job.
