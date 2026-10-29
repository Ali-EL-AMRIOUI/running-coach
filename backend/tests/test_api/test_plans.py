"""
tests/test_api/test_plans.py
API tests for api/plans.py — focused on the authentication fix:
every /plans/* route must require a valid JWT and only expose the
caller's own plans.
"""

from unittest.mock import patch


FAKE_PLAN_DATA = {
    "coach_analysis": "Test analysis",
    "total_km": 100.0,
    "weeks": [],
}


class TestPlansRequireAuth:

    def test_list_plans_without_token_is_rejected(self, client):
        response = client.get("/plans/")
        assert response.status_code in (401, 403)

    def test_generate_without_token_is_rejected(self, client):
        response = client.post("/plans/generate", json={})
        assert response.status_code in (401, 403)

    def test_get_plan_without_token_is_rejected(self, client):
        response = client.get("/plans/1")
        assert response.status_code in (401, 403)

    def test_delete_plan_without_token_is_rejected(self, client):
        response = client.delete("/plans/1")
        assert response.status_code in (401, 403)


class TestPlansWithAuth:

    def test_list_plans_with_token_returns_empty_list(self, client, registered_user):
        response = client.get(
            "/plans/",
            headers={"Authorization": f"Bearer {registered_user['token']}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_get_nonexistent_plan_returns_404(self, client, registered_user):
        response = client.get(
            "/plans/999",
            headers={"Authorization": f"Bearer {registered_user['token']}"},
        )
        assert response.status_code == 404

    @patch("api.plans.AgentOrchestrator.run_workflow", return_value=FAKE_PLAN_DATA)
    def test_generate_plan_saves_under_correct_user(self, mock_run, client, registered_user):
        payload = {
            "age": 30,
            "gender": "M",
            "current_volume": 40,
            "current_frequency": 4,
            "goal_distance": "half",
            "goal_date": "2027-01-01",
            "availability": 4,
            "double_session": "no",
        }
        response = client.post(
            "/plans/generate",
            json=payload,
            headers={"Authorization": f"Bearer {registered_user['token']}"},
        )
        assert response.status_code == 200
        assert response.json()["total_km"] == 100.0

        # Confirm it now shows up when listing this user's plans
        list_response = client.get(
            "/plans/",
            headers={"Authorization": f"Bearer {registered_user['token']}"},
        )
        assert len(list_response.json()) == 1


class TestPlansIsolationBetweenUsers:

    @patch("api.plans.AgentOrchestrator.run_workflow", return_value=FAKE_PLAN_DATA)
    def test_user_cannot_see_another_users_plan(self, mock_run, client, registered_user):
        # User A generates a plan
        payload = {
            "age": 30, "gender": "M", "current_volume": 40,
            "current_frequency": 4, "goal_distance": "half",
            "goal_date": "2027-01-01", "availability": 4, "double_session": "no",
        }
        gen_response = client.post(
            "/plans/generate",
            json=payload,
            headers={"Authorization": f"Bearer {registered_user['token']}"},
        )
        plan_id = gen_response.json()["id"]

        # User B registers separately
        user_b = client.post(
            "/auth/register",
            json={"email": "userb@example.com", "password": "otherpass123"},
        )
        token_b = user_b.json()["access_token"]

        # User B must NOT be able to access User A's plan
        response = client.get(
            f"/plans/{plan_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 404
