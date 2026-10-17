# GramPay Voice Verification

GramPay is a local interface for enrolling a speaker voiceprint with DetectifAI Eidos and checking submitted speech with DetectifAI Aletheia and Eidos. Results are returned from those live provider calls. If credentials, provider access, or credits are unavailable, the check fails closed; it does not create local substitute scores.

## Local setup

1. Install Python 3.11 or newer and the packages in `Backend/requirements.txt`.
2. Configure `DETECTIF_API_KEY` in `Backend/.env`. The app reads this file locally.
3. Start the API from the `Backend` directory:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   py run_server.py
   ```

4. Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The server binds to loopback by default.

## Scope

The current app records/enrolls speech and performs voice checks. It does not connect to a bank, NPCI, UPI, a live payment rail, or a downstream banking agent. Payment, agent-turn, and challenge-verification endpoints fail closed with HTTP 501. Demo and fixture endpoints are disabled. The dashboard shows counts from the current server session; monetary savings are not estimated. Existing audit records remain stored locally.

Keep provider keys in the local `.env` file and do not commit them.
