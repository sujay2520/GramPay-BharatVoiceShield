"""Centralized configuration and security thresholds for GramPay (Voice Payment Gateway for NPCI Hello! UPI and 123Pay protecting farmers & seniors).
Single source of truth for environment variables, operational parameters, and security thresholds.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths & environment loading
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# DetectifAI Platform Settings (Single source of truth)
DETECTIF_API_KEY = os.getenv("DETECTIF_API_KEY", "").strip()
DETECTIF_BASE_URL = os.getenv("DETECTIF_BASE_URL", "https://platform.detectif.ai/v1").rstrip("/")
DETECTIF_TIMEOUT_SECONDS = float(os.getenv("DETECTIF_TIMEOUT_SECONDS", "5.0"))

# NVIDIA Nemotron LLM Settings (Single source of truth)
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")

# Cryptographic & Security Credentials
JWT_SECRET = os.getenv("JWT_SECRET", "unclone_secret_key_bfsi_trust_2026_x892")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
CREDENTIAL_VALIDITY_SECONDS = int(os.getenv("CREDENTIAL_VALIDITY_SECONDS", "300"))  # 5 minutes

# CORS Settings
ALLOWED_ORIGIN = "http://127.0.0.1:8000"

# Cost Optimization Model (INR)
ASSUMED_COST_PER_MIN_INR = float(os.getenv("ASSUMED_COST_PER_MIN_INR", "10.0"))
EST_CALL_SECONDS_SAVED_PER_BLOCK = float(os.getenv("EST_CALL_SECONDS_SAVED_PER_BLOCK", "120.0"))

# GramPay Voice Payment Parameters (NPCI Hello! UPI and 123Pay protecting farmers & seniors)
NPCI_UPI_LIMIT_INR = float(os.getenv("NPCI_UPI_LIMIT_INR", "5000.0"))
DEMO_FARMER_NAME = os.getenv("DEMO_FARMER_NAME", "Ramesh Patel (Kisan Account)")
DEMO_MERCHANT = os.getenv("DEMO_MERCHANT", "IFFCO Fertilizer Co-op")

# Official DetectifAI OpenAPI Thresholds (from platform.detectif.ai openapi spec)
SYNTH_THRESHOLD = float(os.getenv("SYNTH_THRESHOLD", "0.62"))       # verdict fake if >= 0.62
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.53")) # match if >= 0.53

# Dual-Gate Security Matrix Thresholds (3-Tier GramPay Decision Matrix)
SYNTH_HIGH = float(os.getenv("SYNTH_HIGH", "0.62"))  # >= 0.62 indicates synthetic clone (Tier 3: High Risk)
SYNTH_LOW = float(os.getenv("SYNTH_LOW", "0.50"))    # 0.50 - 0.62 indicates medium / uncertain risk (Tier 2)
MATCH_HIGH = float(os.getenv("MATCH_HIGH", "0.53"))  # >= 0.53 indicates authentic enrolled voice (Tier 1: Low Risk)
MATCH_LOW = float(os.getenv("MATCH_LOW", "0.40"))    # 0.40 - 0.53 indicates uncertain match (Tier 2)

# Credit Guardian & Circuit Breaker (Reserve Floor)
CREDIT_RESERVE_FLOOR = int(os.getenv("CREDIT_RESERVE_FLOOR", "3000"))

# SQLite Storage
SQLITE_DB_PATH = Path(os.getenv("SQLITE_DB_PATH", DATA_DIR / "audit.db"))
