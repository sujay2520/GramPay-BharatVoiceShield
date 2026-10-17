"""UnClone Gate Server Runner.
Track 3: UNCLONE Agents - Zero-Trust Voice Security & Cost Optimization Gateway.

Configures and boots the Uvicorn ASGI server with:
- Loopback-only host (127.0.0.1) and port (8000) binding (configurable via HOST / PORT env vars).
- Graceful logging configuration.
- Local-only CORS and network binding.
- Detailed startup banner displaying DetectifAI platform and NVIDIA Nemotron status.
"""

import os
import sys
import logging
from pathlib import Path

# Ensure repository root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn

from backend.config import (
    DETECTIF_API_KEY,
    DETECTIF_BASE_URL,
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NEMOTRON_MODEL,
    MATCH_HIGH,
    SYNTH_HIGH,
    SYNTH_LOW,
    SQLITE_DB_PATH,
    CREDENTIAL_VALIDITY_SECONDS,
    ASSUMED_COST_PER_MIN_INR,
    EST_CALL_SECONDS_SAVED_PER_BLOCK,
)
from backend.detectif_client import detectif_client


def configure_logging(log_level: str = "INFO") -> logging.Logger:
    """Configures structured, graceful logging for the UnClone Gate server."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("unclone.server")
    logger.setLevel(numeric_level)
    return logger


def mask_secret(secret: str) -> str:
    """Safely masks credentials for startup telemetry logging."""
    if not secret or secret == "your_detectifai_api_key_here":
        return "[NOT CONFIGURED / PLACEHOLDER]"
    if len(secret) <= 8:
        return "****"
    return f"{secret[:4]}...{secret[-4:]}"


def print_startup_banner(host: str, port: int, logger: logging.Logger):
    """Prints a comprehensive diagnostic banner detailing system status."""
    banner_border = "=" * 80
    sub_border = "-" * 80

    # Inspect DetectifAI status
    detectif_is_configured = detectif_client.is_configured()
    detectif_key_status = mask_secret(DETECTIF_API_KEY)
    
    try:
        detectif_healthy, health_info = detectif_client.check_health()
        if detectif_healthy:
            detectif_conn_str = f"ONLINE ({health_info.get('latency_ms', '?')}ms latency)"
        else:
            detectif_conn_str = f"OFFLINE ({health_info.get('reason', 'Unreachable')})"
    except Exception as exc:
        detectif_healthy = False
        detectif_conn_str = f"CHECK FAILED ({exc})"

    # Inspect NVIDIA Nemotron status
    nemotron_configured = bool(NVIDIA_API_KEY and NVIDIA_API_KEY.startswith("nvapi-"))
    nemotron_key_status = mask_secret(NVIDIA_API_KEY)

    cors_notice = "Local UI only: localhost and 127.0.0.1 on port 8000"

    print(banner_border)
    print(r"""  _   _            ____ _                     ____       _       
 | | | |_ __   ___/ ___| | ___  _ __   ___   / ___| __ _| |_ ___ 
 | | | | '_ \ / __| |   | |/ _ \| '_ \ / _ \ | |  _ / _` | __/ _ \
 | |_| | | | | (__| |___| | (_) | | | |  __/ | |_| | (_| | ||  __/
  \___/|_| |_|\___|\____|_|\___/|_| |_|\___|  \____|\__,_|\__\___|""")
    print("      TRACK 3: UNCLONE AGENTS | ZERO-TRUST BFSI VOICE SECURITY")
    print(banner_border)
    print(" SYSTEM OVERVIEW & ENDPOINTS:")
    print(f"  * Host Binding       : http://{host}:{port}")
    print(f"  * Swagger UI Docs    : http://localhost:{port}/docs")
    print(f"  * ReDoc Contract     : http://localhost:{port}/redoc")
    print(f"  * Health Check       : http://localhost:{port}/api/health")
    print(f"  * SQLite Audit Store : {SQLITE_DB_PATH}")
    print(sub_border)
    print(" DETECTIFAI DUAL-GATE VOICE ENGINE:")
    print(f"  * API Endpoint       : {DETECTIF_BASE_URL}")
    print(f"  * Credential Status  : {detectif_key_status}")
    print(f"  * Platform Status    : {detectif_conn_str}")
    print(f"  * Strict Mode        : Live verification enforced (Hackathon Rule 5.4)")
    print(sub_border)
    print(" NVIDIA NEMOTRON ORCHESTRATION:")
    print(f"  * API Endpoint       : {NVIDIA_BASE_URL}")
    print(f"  * Active Model       : {NEMOTRON_MODEL}")
    print(f"  * Credential Status  : {nemotron_key_status}")
    print(f"  * Pre-Gate Guard     : Audio verified before LLM token consumption")
    print(sub_border)
    print(" SECURITY MATRIX & THRESHOLDS:")
    print(f"  * MATCH_HIGH (Auth)  : >= {MATCH_HIGH} (Enrolled speaker match)")
    print(f"  * SYNTH_HIGH (Block) : >= {SYNTH_HIGH} (Synthetic/cloned audio detection)")
    print(f"  * SYNTH_LOW (Human)  : <  {SYNTH_LOW} (Natural human speech baseline)")
    print(f"  * Credential TTL     : {CREDENTIAL_VALIDITY_SECONDS}s (5 min cryptographic handshake)")
    print(f"  * Cost Savings Est.  : INR {ASSUMED_COST_PER_MIN_INR}/min (~{EST_CALL_SECONDS_SAVED_PER_BLOCK}s saved/block)")
    print(sub_border)
    print(" CORS POLICY & NETWORK NOTICE:")
    print(f"  * Status             : {cors_notice}")
    print(f"  * Header Config      : Allow-Methods=[*], Allow-Headers=[*]")
    print(banner_border)
    print(flush=True)

    logger.info("UnClone Gate startup banner rendered successfully.")
    logger.info("CORS configuration active: %s", cors_notice)
    if not detectif_is_configured:
        logger.warning(
            "DetectifAI API key is missing or placeholder. Live audio verification calls will fail-closed until configured."
        )


def main():
    """Main execution point for starting the Uvicorn application server."""
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info")
    reload_enabled = os.getenv("RELOAD", "false").lower() in ("true", "1", "yes")

    logger = configure_logging(log_level)
    print_startup_banner(host, port, logger)

    logger.info("Initializing Uvicorn ASGI server on %s:%d (reload=%s)...", host, port, reload_enabled)
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        log_level=log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
