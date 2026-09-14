import os
import tempfile
import unittest
from datetime import date, datetime
from importlib import reload
from pathlib import Path


class FeatureModulesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        db_path = Path(cls.tempdir.name) / "test.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["SECRET_KEY"] = "test-secret-key"

        import config
        import models
        import security
        import schemas
        import routes.auth
        import routes.users
        import routes.audit
        import routes.projects
        import routes.records
        import routes.approval
        import routes.dashboard
        import routes.attendance
        import routes.meetings
        import routes.office_expenses
        import routes.materials
        import app

        reload(config)
        reload(models)
        reload(security)
        reload(schemas)
        reload(routes.auth)
        reload(routes.users)
        reload(routes.audit)
        reload(routes.projects)
        reload(routes.records)
        reload(routes.approval)
        reload(routes.dashboard)
        reload(routes.attendance)
        reload(routes.meetings)
        reload(routes.office_expenses)
        reload(routes.materials)
        cls.app_module = reload(app)

        from fastapi.testclient import TestClient

        cls.client = TestClient(cls.app_module.app)
        with cls.client:
            pass
        token = cls.client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin123"},
        ).json()["access_token"]
        cls.headers = {"Authorization": "Bearer " + token}

        supervisor_payload = {
            "username": "super01",
            "password": "123456",
            "full_name": "监理赵工",
            "role": "supervisor",
        }
        cls.client.post("/api/users", headers=cls.headers, json=supervisor_payload)
        supervisor_token = cls.client.post(
            "/api/auth/login",
            data={"username": "super01", "password": "123456"},
        ).json()["access_token"]
        cls.supervisor_headers = {"Authorization": "Bearer " + supervisor_token}

    @classmethod
    def tearDownClass(cls):
        cls.tempdir.cleanup()

    def test_attendance_statistics_excludes_tuesday(self):
        checkin = self.client.post(
            "/api/attendance/checkin",
            headers=self.supervisor_headers,
            json={"check_time": "2026-09-14T09:20:00"},
        )
        self.assertEqual(checkin.status_code, 200)
        checkout = self.client.post(
            "/api/attendance/checkout",
            headers=self.supervisor_headers,
            json={"check_time": "2026-09-14T17:30:00"},
        )
        self.assertEqual(checkout.status_code, 200)

        stats = self.client.get(
            "/api/attendance/statistics",
            headers=self.supervisor_headers,
            params={"start_date": "2026-09-14", "end_date": "2026-09-16"},
        )
        self.assertEqual(stats.status_code, 200)
        payload = stats.json()
        self.assertEqual(payload["expected_workdays"], 2)
        self.assertEqual(payload["attended_days"], 1)
        self.assertEqual(payload["absent_days"], 1)
        self.assertEqual(payload["late_count"], 1)
        self.assertEqual(payload["early_leave_count"], 1)

    def test_material_outbound_reduces_inventory_after_approval(self):
        material = self.client.post(
            "/api/materials",
            headers=self.headers,
            json={
                "code": "MAT-001",
                "name": "瓷砖",
                "specification": "800x800",
                "unit": "箱",
                "cost_price": 120,
                "category": "建材",
                "warning_quantity": 2,
            },
        )
        self.assertEqual(material.status_code, 201)
        material_id = material.json()["id"]

        inbound = self.client.post(
            "/api/materials/inbounds",
            headers=self.headers,
            json={
                "material_id": material_id,
                "purchase_date": "2026-09-14",
                "supplier": "建材城",
                "unit_price": 120,
                "quantity": 10,
            },
        )
        self.assertEqual(inbound.status_code, 201)

        project = self.client.post(
            "/api/projects",
            headers=self.headers,
            json={
                "name": "样板间工地",
                "contract_number": "HT-001",
                "client_name": "张三",
                "contract_amount": 500000,
                "total_price": 500000,
                "cooperation_type": "full_case",
            },
        )
        self.assertEqual(project.status_code, 201)
        project_id = project.json()["id"]

        outbound = self.client.post(
            "/api/materials/outbounds",
            headers=self.supervisor_headers,
            json={
                "project_id": project_id,
                "project_name": "样板间工地",
                "purpose": "地面铺贴",
                "issue_date": "2026-09-15",
                "items": [{"material_id": material_id, "quantity": 3}],
            },
        )
        self.assertEqual(outbound.status_code, 201)
        outbound_id = outbound.json()["id"]
        self.assertEqual(outbound.json()["status"], "pending")

        approval = self.client.post(f"/api/materials/outbounds/{outbound_id}/approve", headers=self.headers)
        self.assertEqual(approval.status_code, 200)
        self.assertEqual(approval.json()["status"], "approved")

        material_detail = self.client.get(f"/api/materials/{material_id}", headers=self.headers)
        self.assertEqual(material_detail.status_code, 200)
        self.assertEqual(material_detail.json()["current_stock"], 7)

    def test_project_collection_statistics(self):
        project = self.client.post(
            "/api/projects",
            headers=self.headers,
            json={
                "name": "收款测试工地",
                "contract_number": "HT-002",
                "client_name": "李四",
                "contract_amount": 300000,
                "total_price": 300000,
                "cooperation_type": "half_package",
            },
        )
        self.assertEqual(project.status_code, 201)
        project_id = project.json()["id"]

        phases = self.client.post(
            f"/api/projects/{project_id}/payment-phases",
            headers=self.headers,
            json=[
                {"phase_number": 1, "phase_name": "签约", "trigger_progress": 0, "payment_percent": 30, "planned_amount": 90000},
                {"phase_number": 2, "phase_name": "进度 50%", "trigger_progress": 50, "payment_percent": 50, "planned_amount": 150000},
                {"phase_number": 3, "phase_name": "完工", "trigger_progress": 100, "payment_percent": 20, "planned_amount": 60000},
            ],
        )
        self.assertEqual(phases.status_code, 200)
        first_phase_id = phases.json()[0]["id"]

        payment = self.client.post(
            f"/api/projects/payment-phases/{first_phase_id}/record",
            headers=self.headers,
            json={"actual_amount": 90000, "payment_date": "2026-09-16"},
        )
        self.assertEqual(payment.status_code, 200)

        stats = self.client.get("/api/projects/collection-statistics", headers=self.headers)
        self.assertEqual(stats.status_code, 200)
        payload = stats.json()
        target = next(item for item in payload["projects"] if item["contract_number"] == "HT-002")
        self.assertEqual(target["receivable_amount"], 300000.0)
        self.assertEqual(target["received_amount"], 90000.0)
        self.assertEqual(target["collection_progress"], 30.0)


if __name__ == "__main__":
    unittest.main()
