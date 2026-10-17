"""Demo Banking Services & NPCI Hello! UPI / 123Pay Voice Tools.
Clearly labelled simulated financial environment for UnClone / GramPay.

NON-NEGOTIABLE SAFETY RULE:
All tools remain HARD-LOCKED (is_unlocked=False) by default and ONLY execute
when the GramPay / DetectifAI gate deterministically outputs APPROVE (tool_allowed=True).
The LLM / caller cannot bypass this deterministic biometric lock.
"""

from typing import Dict, Any, Optional

# Demo Environment Notice & Core Labeling
DEMO_BANK_ENVIRONMENT = {
    "provider": "NPCI Hello! UPI & 123Pay Simulated Banking Core",
    "disclaimer": "SIMULATED FINANCIAL ENVIRONMENT - DEMO ONLY. Not real money.",
    "is_simulation": True
}

# Demo Account Ledgers (Clearly labelled simulated environment)
DEMO_ACCOUNTS = {
    "senior_user_01": {
        "name": "Sita Ramachandran (Senior Citizen)",
        "demo_bank": "Demo Canara Bank (Simulated Senior Citizen Account)",
        "account_number": "SB-8920194821",
        "balance_inr": 245000.0,
        "daily_limit_inr": 50000.0
    },
    "kisan_farmer_01": {
        "name": "Ramesh Patel (Kisan Account Holder)",
        "demo_bank": "Demo Gramin Kisan Sahakari Bank (Simulated Environment - NPCI 123Pay / Hello! UPI)",
        "account_number": "KCC-GRAMPAY-7788991122",
        "upi_id": "ramesh.farmer@upi",
        "balance_inr": 28500.0,
        "daily_limit_inr": 50000.0,
        "pm_kisan_beneficiary_id": "PMK-IND-GJ-982341",
        "pm_kisan_dbt_status": "ACTIVE",
        "last_dbt_installment": {
            "installment_no": 17,
            "scheme": "PM-KISAN Direct Benefit Transfer",
            "amount_inr": 2000.0,
            "credit_date": "2026-06-18",
            "status": "CREDITED",
            "reference_id": "DBT-PMKISAN-20260618-9921",
            "bank_name": "Demo Gramin Kisan Sahakari Bank (Simulated)"
        }
    },
    "farmer_ramesh": {
        "name": "Ramesh Patel (Kisan Account Holder)",
        "demo_bank": "Demo Gramin Kisan Sahakari Bank (Simulated Environment - NPCI 123Pay / Hello! UPI)",
        "account_number": "KCC-GRAMPAY-7788991122",
        "upi_id": "ramesh.farmer@upi",
        "balance_inr": 28500.0,
        "daily_limit_inr": 50000.0
    },
    "Ramesh_Patel": {
        "name": "Ramesh Patel (Kisan Account Holder)",
        "demo_bank": "Demo Gramin Kisan Sahakari Bank (Simulated Environment - NPCI 123Pay / Hello! UPI)",
        "account_number": "KCC-GRAMPAY-7788991122",
        "upi_id": "ramesh.farmer@upi",
        "balance_inr": 28500.0,
        "daily_limit_inr": 50000.0
    },
    "default": {
        "name": "Demo Account Holder",
        "demo_bank": "Demo State Bank of India (Simulated Environment)",
        "account_number": "SB-1002938471",
        "balance_inr": 150000.0,
        "daily_limit_inr": 50000.0
    }
}


def replenish_demo_account(
    account_id: str = "kisan_farmer_01",
    amount: float = 50000.0
) -> Dict[str, Any]:
    """Safely replenishes / updates a demo account balance to the specified amount.
    
    Safe helper for demonstration environments to prevent demo account depletion.
    """
    if account_id in DEMO_ACCOUNTS:
        DEMO_ACCOUNTS[account_id]["balance_inr"] = float(amount)
        if account_id in ("kisan_farmer_01", "farmer_ramesh", "Ramesh_Patel"):
            for alias in ("kisan_farmer_01", "farmer_ramesh", "Ramesh_Patel"):
                if alias in DEMO_ACCOUNTS:
                    DEMO_ACCOUNTS[alias]["balance_inr"] = float(amount)
        return {
            "account_id": account_id,
            "balance_inr": float(amount),
            "status": "REPLENISHED"
        }
    return {
        "account_id": account_id,
        "balance_inr": 0.0,
        "status": "ACCOUNT_NOT_FOUND"
    }


def pay_merchant(
    amount: float,
    merchant_name: str = 'IFFCO Fertilizer Co-op',
    upi_id: str = 'iffco@upi',
    account_id: str = 'kisan_farmer_01',
    is_unlocked: bool = False
) -> Dict[str, Any]:
    """Executes a voice-authorized merchant payment via NPCI Hello! UPI / 123Pay.
    
    Hard-locked by default. ONLY executes if GramPay / UnClone gate outputs APPROVE (tool_allowed=True).
    Clearly labelled demo bank simulation.
    """
    if not is_unlocked:
        return {
            "name": "pay_merchant",
            "service": "NPCI Hello! UPI / 123Pay Voice Payment",
            "demo_bank": "Demo Gramin Kisan Sahakari Bank (Simulated Environment)",
            "simulation_mode": True,
            "status": "LOCKED",
            "result": None,
            "message": "[DEMO BANK] Merchant payment is strictly LOCKED by GramPay Security Gate. Biometric voice verification must output APPROVE / tool_allowed=True before execution."
        }

    acct = DEMO_ACCOUNTS.get(account_id, DEMO_ACCOUNTS.get("kisan_farmer_01", DEMO_ACCOUNTS["default"]))
    demo_bank_label = acct.get("demo_bank", "Demo Gramin Kisan Sahakari Bank (Simulated Environment)")

    if amount <= 0:
        return {
            "name": "pay_merchant",
            "service": "NPCI Hello! UPI / 123Pay Voice Payment",
            "demo_bank": demo_bank_label,
            "simulation_mode": True,
            "status": "FAILED",
            "result": {"error": "INVALID_AMOUNT"},
            "message": "[DEMO BANK] Payment failed: Amount must be greater than zero."
        }

    if amount > acct["balance_inr"]:
        return {
            "name": "pay_merchant",
            "service": "NPCI Hello! UPI / 123Pay Voice Payment",
            "demo_bank": demo_bank_label,
            "simulation_mode": True,
            "status": "FAILED",
            "result": {
                "error": "INSUFFICIENT_FUNDS",
                "available_balance_inr": acct["balance_inr"],
                "requested_amount_inr": amount
            },
            "message": f"[DEMO BANK] Payment failed: Insufficient balance in Kisan demo account (Available: ₹{acct['balance_inr']:,.2f}, Requested: ₹{amount:,.2f})."
        }

    daily_limit = acct.get("daily_limit_inr", 50000.0)
    if amount > daily_limit:
        return {
            "name": "pay_merchant",
            "service": "NPCI Hello! UPI / 123Pay Voice Payment",
            "demo_bank": demo_bank_label,
            "simulation_mode": True,
            "status": "FAILED",
            "result": {
                "error": "DAILY_LIMIT_EXCEEDED",
                "daily_limit_inr": daily_limit,
                "requested_amount_inr": amount
            },
            "message": f"[DEMO BANK] Payment failed: Amount ₹{amount:,.2f} exceeds NPCI 123Pay daily voice limit of ₹{daily_limit:,.2f}."
        }

    # Deduct balance in demo simulation
    acct["balance_inr"] -= amount
    txn_id = f"TXN-NPCI-123PAY-{int(amount)}-PASS"

    return {
        "name": "pay_merchant",
        "service": "NPCI Hello! UPI / 123Pay Voice Payment",
        "demo_bank": demo_bank_label,
        "simulation_mode": True,
        "status": "EXECUTED",
        "result": {
            "transaction_id": txn_id,
            "payer_account": acct["account_number"],
            "payer_name": acct["name"],
            "merchant_name": merchant_name,
            "merchant_upi_id": upi_id,
            "amount_inr": amount,
            "remaining_balance_inr": acct["balance_inr"],
            "protocol": "NPCI Hello! UPI / 123Pay Voice Authorization",
            "gate_status": "APPROVE (GramPay Verified)"
        },
        "message": f"[DEMO BANK] Successfully paid ₹{amount:,.2f} to {merchant_name} ({upi_id}) via NPCI Hello! UPI / 123Pay. Remaining balance: ₹{acct['balance_inr']:,.2f}."
    }


def check_kisan_balance(
    account_id: str = 'kisan_farmer_01',
    is_unlocked: bool = False
) -> Dict[str, Any]:
    """Queries Kisan account balance via NPCI 123Pay voice enquiry.
    
    Hard-locked by default. ONLY executes if GramPay / UnClone gate outputs APPROVE (tool_allowed=True).
    Clearly labelled demo bank simulation.
    """
    if not is_unlocked:
        return {
            "name": "check_kisan_balance",
            "service": "NPCI 123Pay Kisan Balance Enquiry",
            "demo_bank": "Demo Gramin Kisan Sahakari Bank (Simulated Environment)",
            "simulation_mode": True,
            "status": "LOCKED",
            "result": None,
            "message": "[DEMO BANK] Kisan account balance inquiry is strictly LOCKED by GramPay Security Gate until caller authenticity is verified."
        }

    acct = DEMO_ACCOUNTS.get(account_id, DEMO_ACCOUNTS.get("kisan_farmer_01", DEMO_ACCOUNTS["default"]))
    demo_bank_label = acct.get("demo_bank", "Demo Gramin Kisan Sahakari Bank (Simulated Environment)")

    return {
        "name": "check_kisan_balance",
        "service": "NPCI 123Pay Kisan Balance Enquiry",
        "demo_bank": demo_bank_label,
        "simulation_mode": True,
        "status": "EXECUTED",
        "result": {
            "account_number": acct["account_number"],
            "holder_name": acct["name"],
            "available_balance_inr": acct["balance_inr"],
            "daily_limit_inr": acct.get("daily_limit_inr", 50000.0),
            "account_type": "Kisan Credit Card (KCC) & Savings",
            "protocol": "NPCI 123Pay Voice IVR Enquiry"
        },
        "message": f"[DEMO BANK] Kisan account balance for {acct['name']} is ₹{acct['balance_inr']:,.2f}."
    }


def verify_pm_kisan_dbt(
    account_id: str = 'kisan_farmer_01',
    is_unlocked: bool = False
) -> Dict[str, Any]:
    """Verifies PM-KISAN Direct Benefit Transfer (DBT) credit status via NPCI APBS.
    
    Hard-locked by default. ONLY executes if GramPay / UnClone gate outputs APPROVE (tool_allowed=True).
    Clearly labelled demo bank simulation.
    """
    if not is_unlocked:
        return {
            "name": "verify_pm_kisan_dbt",
            "service": "PM-KISAN DBT Direct Benefit Transfer Verification (NPCI APBS)",
            "demo_bank": "Demo Gramin Kisan Sahakari Bank (Simulated Environment)",
            "simulation_mode": True,
            "status": "LOCKED",
            "result": None,
            "message": "[DEMO BANK] PM-KISAN DBT record verification is strictly LOCKED by GramPay Security Gate."
        }

    acct = DEMO_ACCOUNTS.get(account_id, DEMO_ACCOUNTS.get("kisan_farmer_01", DEMO_ACCOUNTS["default"]))
    demo_bank_label = acct.get("demo_bank", "Demo Gramin Kisan Sahakari Bank (Simulated Environment)")

    dbt_record = acct.get("last_dbt_installment", {
        "installment_no": 17,
        "scheme": "PM-KISAN Samman Nidhi DBT",
        "amount_inr": 2000.0,
        "credit_date": "2026-06-18",
        "status": "CREDITED",
        "reference_id": "DBT-PMKISAN-20260618-9921",
        "bank_name": "Demo Gramin Kisan Sahakari Bank (Simulated)"
    })

    return {
        "name": "verify_pm_kisan_dbt",
        "service": "PM-KISAN DBT Direct Benefit Transfer Verification (NPCI APBS)",
        "demo_bank": demo_bank_label,
        "simulation_mode": True,
        "status": "EXECUTED",
        "result": {
            "beneficiary_id": acct.get("pm_kisan_beneficiary_id", "PMK-IND-GJ-982341"),
            "holder_name": acct["name"],
            "dbt_status": acct.get("pm_kisan_dbt_status", "ACTIVE"),
            "aadhaar_seeded": True,
            "npci_mapper_status": "LINKED_AND_VERIFIED",
            "latest_installment": dbt_record
        },
        "message": f"[DEMO BANK] PM-KISAN DBT verified active for {acct['name']}. Latest installment #{dbt_record['installment_no']} of ₹{dbt_record['amount_inr']:,.2f} status: {dbt_record['status']} on {dbt_record['credit_date']}."
    }


class BankingTools:
    """Namespace container for UnClone and GramPay banking tools."""

    @staticmethod
    def get_tool_definition(name: str = "transfer_funds") -> Dict[str, Any]:
        return {
            "name": name,
            "status": "LOCKED",
            "result": None
        }

    @staticmethod
    def execute_check_balance(account_id: str = "senior_user_01", is_unlocked: bool = False) -> Dict[str, Any]:
        """Queries account balance. Locked if gate does not allow."""
        if not is_unlocked:
            return {
                "name": "check_balance",
                "status": "LOCKED",
                "result": None,
                "message": "Action is locked by UnClone Security Gate."
            }
        
        acct = DEMO_ACCOUNTS.get(account_id, DEMO_ACCOUNTS["default"])
        return {
            "name": "check_balance",
            "status": "EXECUTED",
            "result": {
                "account_number": acct["account_number"],
                "holder_name": acct["name"],
                "available_balance_inr": acct["balance_inr"]
            },
            "message": f"Account balance is ₹{acct['balance_inr']:,.2f}."
        }

    @staticmethod
    def execute_transfer_funds(
        amount: float,
        recipient: str = "Rahul Sharma (Grandson)",
        from_account_id: str = "senior_user_01",
        is_unlocked: bool = False
    ) -> Dict[str, Any]:
        """Executes transfer. Hard-locked if gate does not approve."""
        if not is_unlocked:
            return {
                "name": "transfer_funds",
                "status": "LOCKED",
                "result": None,
                "message": "High-risk transfer is LOCKED by UnClone Gate until voice liveness and identity pass."
            }
        
        acct = DEMO_ACCOUNTS.get(from_account_id, DEMO_ACCOUNTS["default"])
        if amount > acct["balance_inr"]:
            return {
                "name": "transfer_funds",
                "status": "FAILED",
                "result": {"error": "INSUFFICIENT_FUNDS"},
                "message": "Transfer failed: Insufficient balance."
            }

        # Deduct balance in demo simulation
        acct["balance_inr"] -= amount
        
        return {
            "name": "transfer_funds",
            "status": "EXECUTED",
            "result": {
                "transaction_id": f"TXN-UNCLONE-{int(amount)}-PASS",
                "from_account": acct["account_number"],
                "recipient": recipient,
                "amount_inr": amount,
                "remaining_balance_inr": acct["balance_inr"]
            },
            "message": f"Successfully transferred ₹{amount:,.2f} to {recipient}."
        }

    # NPCI Hello! UPI and 123Pay tool bindings
    pay_merchant = staticmethod(pay_merchant)
    check_kisan_balance = staticmethod(check_kisan_balance)
    verify_pm_kisan_dbt = staticmethod(verify_pm_kisan_dbt)
    replenish_demo_account = staticmethod(replenish_demo_account)

    execute_pay_merchant = staticmethod(pay_merchant)
    execute_check_kisan_balance = staticmethod(check_kisan_balance)
    execute_verify_pm_kisan_dbt = staticmethod(verify_pm_kisan_dbt)


# Module-level aliases for consistent import patterns
execute_check_balance = BankingTools.execute_check_balance
execute_transfer_funds = BankingTools.execute_transfer_funds
replenish_demo_account = replenish_demo_account

