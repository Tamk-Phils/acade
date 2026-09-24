"""
Unit tests for AcadFormat Authentication, RBAC, Device Locking,
72-hour Free Trial, MTN MoMo / Orange Money Paywall (250 FCFA), and Admin Management.
"""
import unittest
import os
import datetime
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import (
    LOCAL_DB_PATH, create_user, authenticate_user,
    check_download_eligibility, record_payment, extend_user_subscription
)

client = TestClient(app)

class TestAuthAndPaywall(unittest.TestCase):
    def test_signup_validation(self):
        # 1. Privacy policy acceptance required
        res = client.post("/api/auth/signup", json={
            "full_name": "Test Student",
            "username": "teststudent1",
            "email": "test1@univ.cm",
            "password": "Password123!",
            "privacy_accepted": False,
            "device_id": "device_alpha"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Privacy Policy", res.json()["detail"])

        # 2. Valid signup
        unique_user = f"student_{datetime.datetime.now().timestamp()}"
        res = client.post("/api/auth/signup", json={
            "full_name": "Njitapon Ahmed Said Assan",
            "username": unique_user,
            "email": f"{unique_user}@univ-bamenda.cm",
            "password": "AssanPassword@2026",
            "confirm_password": "AssanPassword@2026",
            "privacy_accepted": True,
            "device_id": "device_assan_laptop"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["session_token"])
        self.assertEqual(data["user"]["role"], "user")
        self.assertTrue(data["eligibility"]["allowed"])
        self.assertEqual(data["eligibility"]["reason"], "free_trial")

    def test_device_locking_and_paywall(self):
        unique_user = f"devlock_{datetime.datetime.now().timestamp()}"
        email = f"{unique_user}@univ.cm"
        reg_res = client.post("/api/auth/signup", json={
            "full_name": "Device Lock Test User",
            "username": unique_user,
            "email": email,
            "password": "SecurePassword@123",
            "privacy_accepted": True,
            "device_id": "original_phone"
        })
        self.assertEqual(reg_res.status_code, 200)
        user_id = reg_res.json()["user"]["id"]
        token = reg_res.json()["session_token"]

        # Check eligibility on registered device
        elig_orig = check_download_eligibility(user_id, "original_phone")
        self.assertTrue(elig_orig["allowed"], "Original device should have free trial access")

        # Check eligibility on a DIFFERENT device (simulating credential sharing)
        elig_shared = check_download_eligibility(user_id, "friend_laptop")
        self.assertFalse(elig_shared["allowed"], "Shared device must NOT have access without payment")
        self.assertEqual(elig_shared["reason"], "device_mismatch")

        # Now pay 250 FCFA on the new device via MTN MoMo
        pay_res = client.post(
            "/api/payments/momo-checkout",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "operator": "mtn_momo",
                "phone_number": "677123456",
                "device_id": "friend_laptop",
                "amount": 250
            }
        )
        self.assertEqual(pay_res.status_code, 200)
        p_data = pay_res.json()
        self.assertEqual(p_data["status"], "success")
        self.assertEqual(p_data["payment"]["amount"], 250)
        self.assertEqual(p_data["payment"]["operator"], "mtn_momo")

        # Now friend_laptop should be authorized
        elig_after_pay = check_download_eligibility(user_id, "friend_laptop")
        self.assertTrue(elig_after_pay["allowed"], "After paying 250 FCFA, export access should be unlocked")
        self.assertTrue(elig_after_pay["paid_active"])

    def test_rbac_and_admin_endpoints(self):
        # 1. Login as Super Admin
        sa_res = client.post("/api/auth/login", json={
            "identifier": "superadmin",
            "password": "SuperAdmin@2026",
            "device_id": "master_device"
        })
        self.assertEqual(sa_res.status_code, 200)
        sa_token = sa_res.json()["session_token"]

        # Super admin can view analytics
        ana_res = client.get("/api/superadmin/analytics", headers={"Authorization": f"Bearer {sa_token}"})
        self.assertEqual(ana_res.status_code, 200)
        analytics = ana_res.json()["analytics"]
        self.assertIn("total_revenue_xaf", analytics)
        self.assertIn("operator_breakdown", analytics)

        # Super admin can update pricing configuration
        cfg_res = client.post("/api/superadmin/config", headers={"Authorization": f"Bearer {sa_token}"}, json={
            "trial_duration_hours": 72,
            "subscription_price_xaf": 250,
            "subscription_duration_days": 7
        })
        self.assertEqual(cfg_res.status_code, 200)

        # 2. Login as regular Admin
        ad_res = client.post("/api/auth/login", json={
            "identifier": "admin",
            "password": "Admin@2026",
            "device_id": "admin_device"
        })
        self.assertEqual(ad_res.status_code, 200)
        ad_token = ad_res.json()["session_token"]

        # Admin can view user list
        users_res = client.get("/api/admin/users", headers={"Authorization": f"Bearer {ad_token}"})
        self.assertEqual(users_res.status_code, 200)
        self.assertGreaterEqual(len(users_res.json()["users"]), 2)

        # Admin cannot access super admin financial analytics
        denied_res = client.get("/api/superadmin/analytics", headers={"Authorization": f"Bearer {ad_token}"})
        self.assertEqual(denied_res.status_code, 403)

    def test_privacy_policy_endpoint(self):
        res = client.get("/api/privacy-policy")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Law No. 2010/012", res.json()["governing_law"])

    def test_academic_data_and_catuc(self):
        res = client.get("/api/academic-data")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("universities", data)
        self.assertIn("catuc", data["universities"])
        self.assertIn("uba", data["universities"])
        self.assertIn("establishments", data)
        self.assertIn("coltech", data["establishments"])
        self.assertIn("catuc_seng", data["establishments"])
        self.assertIn("catuc_fbms", data["establishments"])

    def test_chat_endpoint(self):
        # 1. Test margin query
        res = client.post("/api/chat", json={
            "message": "What is the inside binding margin?",
            "institution": "uba"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("4.0 cm", data["reply"])

        # 2. Test CATUC query
        res_catuc = client.post("/api/chat", json={
            "message": "Tell me about Catholic University rules",
            "institution": "catuc"
        })
        self.assertEqual(res_catuc.status_code, 200)
        data_catuc = res_catuc.json()
        self.assertIn("Fides et Scientia", data_catuc["reply"])

        # 3. Test pricing query
        res_price = client.post("/api/chat", json={
            "message": "How much does it cost after free trial?",
            "institution": "uba"
        })
        self.assertEqual(res_price.status_code, 200)
        self.assertIn("250 FCFA", res_price.json()["reply"])

    def test_cloudflare_d1_integration(self):
        # 1. Health check returns Cloudflare D1 details
        res = client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("database", data)
        db_info = data["database"]
        self.assertIn("cloudflare_d1", db_info)
        self.assertEqual(db_info["cloudflare_d1"]["database_id"], "1ce80e78-f367-494d-aa47-5c87a8e02613")

        # 2. Schema and config files exist
        self.assertTrue(os.path.exists("cloudflare_d1_schema.sql"))
        with open("cloudflare_d1_schema.sql", "r") as f:
            schema_content = f.read()
        self.assertIn("acadformat_users", schema_content)
        self.assertIn("acadformat_documents", schema_content)

        # 3. Wrangler configuration exists
        self.assertTrue(os.path.exists("wrangler.toml"))
        with open("wrangler.toml", "r") as f:
            wrangler_content = f.read()
        self.assertIn("1ce80e78-f367-494d-aa47-5c87a8e02613", wrangler_content)

if __name__ == "__main__":
    unittest.main()



