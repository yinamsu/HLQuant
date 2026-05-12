# HLQuant Worklog

## 2026-05-12
### Initial Setup & Infrastructure
- Initialized Git repository with `yinamsu` account.
- Set up project structure: `src/`, `docs/`, `tests/`, `data/`.
- Created initial `.gitignore` and `README.md`.

### Core Development
- Implemented `HyperliquidAPI` for market data collection.
- Implemented `DeltaNeutralStrategy` with:
    - APY calculation and filtering.
    - Virtual Slippage Guard (+0.05% buy / -0.05% sell).
    - Minimum Hold Time (8 hours) protection.
- Implemented `main.py` execution loop.

### Debugging & Optimization
- **DNS Fix**: Resolved `aiohttp` DNS resolution issue using `ThreadedResolver`.
- **Spot Mapping Fix**: Corrected logic to map Perp symbols to Spot token metadata (handling `@1`, `@2` aliases).
- **Price Extraction Fix**: Corrected field names from `midPrice` to `midPx` and handled `None` values in API responses.

### Testing Phase
- Lowered APY thresholds to 3.0% for verification.
- Confirmed successful virtual entries for **APT, AVAX, GMT**.
- Verified state persistence in `paper_balance.json`.

---
## 2026-05-12 (Continued)
### Deployment Planning (GCP Server)
- Target Server: Existing GCP instance (`34.136.45.224`).
- Isolation Strategy:
    - Dedicated directory: `~/HLQuant`
    - Dedicated Virtual Environment: `~/HLQuant/venv`
    - Dedicated Systemd Service: `hlquant.service`
- Deployment Automation:
    - Implementation of a `deploy.sh` script to pull latest changes and restart the service.
    - Integration with Git push workflow (manual trigger or webhook).

### Script Creation
- Created `requirements.txt` with essential dependencies.
- Created `deploy.sh` for automated updates and service restarts.
- Created `setup_server.sh` for initial server-side environment setup.
- Created `docs/hlquant.service` systemd unit file template.

### Automation & CI/CD
- Planned GitHub Actions workflow for automatic deployment.
- Required secrets: `REMOTE_HOST`, `REMOTE_USER`, `SSH_PRIVATE_KEY`.
- Created `.github/workflows/deploy.yml` to trigger `./deploy.sh` on push.
- **SSH Key Registration**: Generated a new key pair and registered the public key on the server and the private key on GitHub.
- **Test Deployment**: Triggered a test deployment to verify the full pipeline.
- **Success**: Verified that GitHub Actions successfully connects to the GCP server and executes `./deploy.sh`.
- **Optimization**: Cleaned up `requirements.txt` by removing redundant packages identified during the first deployment.
- **Security & Backup**: Created a local `.env` file (Git ignored) to securely back up the SSH private key and store Telegram API credentials for future notification integration.

### Telegram Notification Integration
- Created `notifier.py` for asynchronous Telegram messaging.
- Integrated `TelegramNotifier` into `strategy.py` for Entry/Exit alerts.
- Added startup notification in `main.py`.
- **Interactive Command Implementation**:
    - Added `/server` command to view CPU, RAM, and Disk status.
    - Implemented a command listener loop in `main.py` (checks every 5 seconds).
    - Updated `requirements.txt` with `psutil`.

---
*Next Step: Long-term monitoring and further command implementation.*
