"""Agent-to-Agent Cryptographic Handshake & Credential Service.
Provides Track 3 proof-of-identity: Prevents rogue bots and man-in-the-middle attacks.

Generates and validates signed, single-use, scoped JWT credentials.
"""

import time
import uuid
import jwt
from typing import Dict, Any, List, Optional
from backend.config import JWT_SECRET, JWT_ALGORITHM, CREDENTIAL_VALIDITY_SECONDS
from backend.audit import record_used_credential

class CredentialService:
    @staticmethod
    def issue_credential(
        agent_id: str,
        org: str,
        allowed_actions: List[str],
        limit_inr: float = 50000.0,
        validity_seconds: int = CREDENTIAL_VALIDITY_SECONDS
    ) -> Dict[str, Any]:
        """Issues an expiring, cryptographically signed, single-use agent credential."""
        now = int(time.time())
        jti = str(uuid.uuid4())
        
        payload = {
            "iss": "UnClone-Agent-Trust-Registry",
            "sub": agent_id,
            "org": org,
            "actions": allowed_actions,
            "limit_inr": limit_inr,
            "jti": jti,
            "iat": now,
            "exp": now + validity_seconds
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return {
            "credential": token,
            "agent_id": agent_id,
            "org": org,
            "jti": jti,
            "expires_in_seconds": validity_seconds,
            "allowed_actions": allowed_actions,
            "limit_inr": limit_inr
        }

    @staticmethod
    def verify_handshake(credential_str: str, required_action: Optional[str] = None) -> Dict[str, Any]:
        """Validates agent credential string against all 4 security checks.
        
        1. Signature check (Cryptographic integrity)
        2. Expiry check (Freshness)
        3. Unused check (Single-use replay prevention via SQLite)
        4. Scope check (Authorized intents)
        """
        checks = {
            "signature": False,
            "expiry": False,
            "unused": False,
            "scope": False
        }

        if not credential_str:
            return {
                "badge": "REJECTED",
                "reason": "Missing agent credential token.",
                "checks": checks
            }

        # Step 1 & 2: Cryptographic signature and expiration check
        try:
            payload = jwt.decode(
                credential_str,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": True}
            )
            checks["signature"] = True
            checks["expiry"] = True
        except jwt.ExpiredSignatureError:
            checks["signature"] = True
            checks["expiry"] = False
            return {
                "badge": "REJECTED",
                "reason": "Agent credential has expired. Handshake rejected.",
                "checks": checks
            }
        except jwt.InvalidTokenError as e:
            return {
                "badge": "REJECTED",
                "reason": f"Invalid cryptographic signature: {str(e)}",
                "checks": checks
            }

        # Step 3: Single-use replay protection
        jti = payload.get("jti")
        agent_id = payload.get("sub", "unknown")
        org = payload.get("org", "unknown")
        
        if not jti:
            return {
                "badge": "REJECTED",
                "reason": "Credential missing unique JTI identifier.",
                "checks": checks
            }

        was_recorded = record_used_credential(jti, agent_id, org)
        if not was_recorded:
            checks["unused"] = False
            return {
                "badge": "REJECTED",
                "reason": "REPLAY ATTACK DETECTED: This single-use agent credential has already been redeemed.",
                "checks": checks
            }
        
        checks["unused"] = True

        # Step 4: Scope / Permission check
        allowed_actions = payload.get("actions", [])
        if required_action:
            if required_action in allowed_actions or "ALL" in allowed_actions:
                checks["scope"] = True
            else:
                checks["scope"] = False
                return {
                    "badge": "REJECTED",
                    "reason": f"Unauthorized action: '{required_action}' is not in agent's allowed scope {allowed_actions}.",
                    "checks": checks
                }
        else:
            checks["scope"] = bool(allowed_actions)

        # All checks passed! Issue Verified Agent Badge
        return {
            "badge": "VERIFIED_AGENT",
            "reason": f"Cryptographically verified agent from {org} ({agent_id}). Safe to interact.",
            "agent_id": agent_id,
            "org": org,
            "limit_inr": payload.get("limit_inr"),
            "checks": checks
        }

credential_service = CredentialService()
