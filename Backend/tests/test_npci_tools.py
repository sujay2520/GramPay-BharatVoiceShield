"""Unit tests for NPCI Hello! UPI and 123Pay banking tools.
Verifies that:
1. pay_merchant, check_kisan_balance, verify_pm_kisan_dbt are strictly LOCKED by default (is_unlocked=False).
2. Tools only execute when is_unlocked=True.
3. Proper demo bank labeling and simulation badges are present.
4. Edge cases like invalid amount, insufficient balance, daily limits are handled gracefully.
"""

import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.tools import (
    pay_merchant,
    check_kisan_balance,
    verify_pm_kisan_dbt,
    replenish_demo_account,
    BankingTools,
    DEMO_ACCOUNTS,
    DEMO_BANK_ENVIRONMENT
)


class TestNPCIBankingTools(unittest.TestCase):
    def setUp(self):
        # Reset kisan_farmer_01 balance before each test to guarantee determinism
        if "kisan_farmer_01" in DEMO_ACCOUNTS:
            DEMO_ACCOUNTS["kisan_farmer_01"]["balance_inr"] = 28500.0

    # --------------------------------------------------------------------------
    # 1. Default Hard-Locked Behavior (Fail-Closed)
    # --------------------------------------------------------------------------
    def test_pay_merchant_locked_by_default(self):
        """pay_merchant must be strictly LOCKED by default without explicit unlock."""
        res = pay_merchant(amount=1500.0)
        self.assertEqual(res["status"], "LOCKED")
        self.assertIsNone(res["result"])
        self.assertIn("GramPay Security Gate", res["message"])
        self.assertTrue(res.get("simulation_mode"))
        self.assertIn("demo_bank", res)

    def test_check_kisan_balance_locked_by_default(self):
        """check_kisan_balance must be strictly LOCKED by default."""
        res = check_kisan_balance()
        self.assertEqual(res["status"], "LOCKED")
        self.assertIsNone(res["result"])
        self.assertIn("GramPay Security Gate", res["message"])
        self.assertTrue(res.get("simulation_mode"))
        self.assertIn("demo_bank", res)

    def test_verify_pm_kisan_dbt_locked_by_default(self):
        """verify_pm_kisan_dbt must be strictly LOCKED by default."""
        res = verify_pm_kisan_dbt()
        self.assertEqual(res["status"], "LOCKED")
        self.assertIsNone(res["result"])
        self.assertIn("GramPay Security Gate", res["message"])
        self.assertTrue(res.get("simulation_mode"))
        self.assertIn("demo_bank", res)

    # --------------------------------------------------------------------------
    # 2. Unlocked Execution & Correct Defaults
    # --------------------------------------------------------------------------
    def test_pay_merchant_unlocked_execution_with_defaults(self):
        """pay_merchant executes when is_unlocked=True with correct defaults."""
        initial_balance = DEMO_ACCOUNTS["kisan_farmer_01"]["balance_inr"]
        res = pay_merchant(amount=2500.0, is_unlocked=True)
        self.assertEqual(res["status"], "EXECUTED")
        self.assertIsNotNone(res["result"])
        self.assertEqual(res["result"]["merchant_name"], "IFFCO Fertilizer Co-op")
        self.assertEqual(res["result"]["merchant_upi_id"], "iffco@upi")
        self.assertEqual(res["result"]["amount_inr"], 2500.0)
        self.assertEqual(res["result"]["remaining_balance_inr"], initial_balance - 2500.0)
        self.assertIn("TXN-NPCI-123PAY", res["result"]["transaction_id"])
        self.assertIn("[DEMO BANK]", res["message"])
        self.assertTrue(res["simulation_mode"])
        self.assertIn("Demo Gramin Kisan Sahakari Bank", res["demo_bank"])

    def test_check_kisan_balance_unlocked_execution(self):
        """check_kisan_balance returns kisan account details when is_unlocked=True."""
        res = check_kisan_balance(is_unlocked=True)
        self.assertEqual(res["status"], "EXECUTED")
        self.assertIsNotNone(res["result"])
        self.assertEqual(res["result"]["holder_name"], DEMO_ACCOUNTS["kisan_farmer_01"]["name"])
        self.assertEqual(res["result"]["available_balance_inr"], 28500.0)
        self.assertEqual(res["result"]["account_type"], "Kisan Credit Card (KCC) & Savings")
        self.assertIn("123Pay", res["result"]["protocol"])
        self.assertIn("[DEMO BANK]", res["message"])
        self.assertTrue(res["simulation_mode"])

    def test_verify_pm_kisan_dbt_unlocked_execution(self):
        """verify_pm_kisan_dbt returns DBT status and installment details when is_unlocked=True."""
        res = verify_pm_kisan_dbt(is_unlocked=True)
        self.assertEqual(res["status"], "EXECUTED")
        self.assertIsNotNone(res["result"])
        self.assertEqual(res["result"]["beneficiary_id"], "PMK-IND-GJ-982341")
        self.assertEqual(res["result"]["dbt_status"], "ACTIVE")
        self.assertTrue(res["result"]["aadhaar_seeded"])
        self.assertEqual(res["result"]["npci_mapper_status"], "LINKED_AND_VERIFIED")
        latest = res["result"]["latest_installment"]
        self.assertEqual(latest["installment_no"], 17)
        self.assertEqual(latest["amount_inr"], 2000.0)
        self.assertEqual(latest["status"], "CREDITED")
        self.assertIn("[DEMO BANK]", res["message"])
        self.assertTrue(res["simulation_mode"])

    # --------------------------------------------------------------------------
    # 3. Class Method Bindings on BankingTools
    # --------------------------------------------------------------------------
    def test_banking_tools_class_bindings(self):
        """BankingTools provides static methods and execute_* aliases for new NPCI tools."""
        res_pay = BankingTools.pay_merchant(amount=100.0, is_unlocked=False)
        self.assertEqual(res_pay["status"], "LOCKED")

        res_bal = BankingTools.check_kisan_balance(is_unlocked=False)
        self.assertEqual(res_bal["status"], "LOCKED")

        res_dbt = BankingTools.verify_pm_kisan_dbt(is_unlocked=False)
        self.assertEqual(res_dbt["status"], "LOCKED")

        # Also test execute_* aliases
        self.assertEqual(BankingTools.execute_pay_merchant(amount=50.0)["status"], "LOCKED")
        self.assertEqual(BankingTools.execute_check_kisan_balance()["status"], "LOCKED")
        self.assertEqual(BankingTools.execute_verify_pm_kisan_dbt()["status"], "LOCKED")

    # --------------------------------------------------------------------------
    # 4. Financial Validation and Guardrails
    # --------------------------------------------------------------------------
    def test_pay_merchant_invalid_amount(self):
        """Zero or negative amounts must fail."""
        res_zero = pay_merchant(amount=0.0, is_unlocked=True)
        self.assertEqual(res_zero["status"], "FAILED")
        self.assertEqual(res_zero["result"]["error"], "INVALID_AMOUNT")

        res_neg = pay_merchant(amount=-500.0, is_unlocked=True)
        self.assertEqual(res_neg["status"], "FAILED")
        self.assertEqual(res_neg["result"]["error"], "INVALID_AMOUNT")

    def test_pay_merchant_insufficient_funds(self):
        """Payment exceeding available balance must fail with INSUFFICIENT_FUNDS."""
        res = pay_merchant(amount=999999.0, is_unlocked=True)
        self.assertEqual(res["status"], "FAILED")
        self.assertEqual(res["result"]["error"], "INSUFFICIENT_FUNDS")

    def test_pay_merchant_daily_limit_exceeded(self):
        """Payment exceeding daily limit must fail with DAILY_LIMIT_EXCEEDED."""
        DEMO_ACCOUNTS["kisan_farmer_01"]["balance_inr"] = 100000.0
        res = pay_merchant(amount=55000.0, is_unlocked=True)
        self.assertEqual(res["status"], "FAILED")
        self.assertEqual(res["result"]["error"], "DAILY_LIMIT_EXCEEDED")


class TestDemoAccountAutoReplenish(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        DEMO_ACCOUNTS["kisan_farmer_01"]["balance_inr"] = 28500.0
        DEMO_ACCOUNTS["senior_user_01"]["balance_inr"] = 245000.0

    def test_replenish_demo_account_valid(self):
        """replenish_demo_account updates balance and synced aliases."""
        res = replenish_demo_account("kisan_farmer_01", 50000.0)
        self.assertEqual(res["status"], "REPLENISHED")
        self.assertEqual(res["balance_inr"], 50000.0)
        self.assertEqual(DEMO_ACCOUNTS["kisan_farmer_01"]["balance_inr"], 50000.0)
        self.assertEqual(DEMO_ACCOUNTS["farmer_ramesh"]["balance_inr"], 50000.0)
        self.assertEqual(DEMO_ACCOUNTS["Ramesh_Patel"]["balance_inr"], 50000.0)

    def test_replenish_demo_account_safe_on_unknown_id(self):
        """replenish_demo_account does not crash on unknown account ID."""
        res = replenish_demo_account("nonexistent_account_99", 50000.0)
        self.assertEqual(res["status"], "ACCOUNT_NOT_FOUND")
        self.assertEqual(res["balance_inr"], 0.0)

    def test_banking_tools_replenish_demo_account_binding(self):
        """BankingTools.replenish_demo_account is callable as a class method."""
        res = BankingTools.replenish_demo_account("senior_user_01", 245000.0)
        self.assertEqual(res["status"], "REPLENISHED")
        self.assertEqual(DEMO_ACCOUNTS["senior_user_01"]["balance_inr"], 245000.0)

    def test_quick_test_authentic_auto_replenish_when_below_15000(self):
        """Inside demo_quick_test_endpoint, if balance < 15000.0, it is auto-replenished to 50000.0 before execution."""
        DEMO_ACCOUNTS["kisan_farmer_01"]["balance_inr"] = 10000.0
        resp = self.client.post("/api/demo/quick-test/authentic?amount=5000.0")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["scenario"], "authentic")
        self.assertEqual(data["decision"], "APPROVE")
        self.assertEqual(data["tool"]["status"], "EXECUTED")
        # 50000 - 5000 = 45000
        self.assertEqual(data["tool"]["result"]["remaining_balance_inr"], 45000.0)
        self.assertEqual(DEMO_ACCOUNTS["kisan_farmer_01"]["balance_inr"], 45000.0)

    def test_quick_test_reset_scenario_explicit_balances(self):
        """When scenario == 'reset', explicitly resets kisan_farmer_01 to 28500 and senior_user_01 to 245000."""
        DEMO_ACCOUNTS["kisan_farmer_01"]["balance_inr"] = 5000.0
        DEMO_ACCOUNTS["senior_user_01"]["balance_inr"] = 10000.0
        resp = self.client.post("/api/demo/quick-test/reset")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["scenario"], "reset")
        self.assertEqual(data["balances"]["kisan_farmer_01"], 28500.0)
        self.assertEqual(data["balances"]["senior_user_01"], 245000.0)
        self.assertEqual(DEMO_ACCOUNTS["kisan_farmer_01"]["balance_inr"], 28500.0)
        self.assertEqual(DEMO_ACCOUNTS["senior_user_01"]["balance_inr"], 245000.0)


if __name__ == "__main__":
    unittest.main()

