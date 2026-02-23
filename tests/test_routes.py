"""tests/test_routes.py — Flask route tests using the test client."""

import json
import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(output_dir=str(tmp_path))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


VALID_PAYLOAD = {
    "army_a": [
        {"unit_id": "A_B1", "team": "A", "type": "Barbarian", "row": 0, "col": 0,
         "move_behavior": "Advance", "attack_behavior": "Closest"},
        {"unit_id": "A_B2", "team": "A", "type": "Barbarian", "row": 1, "col": 1,
         "move_behavior": "Advance", "attack_behavior": "Closest"},
    ],
    "army_b": [
        {"unit_id": "B_AR1", "team": "B", "type": "Archer", "row": 0, "col": 4,
         "move_behavior": "Hold", "attack_behavior": "Closest"},
        {"unit_id": "B_AR2", "team": "B", "type": "Archer", "row": 1, "col": 3,
         "move_behavior": "Hold", "attack_behavior": "LowestHP"},
    ],
}


class TestSetupRoute:

    def test_get_setup(self, client):
        res = client.get("/setup")
        assert res.status_code == 200
        assert b"Army Builder" in res.data

    def test_root_redirects_to_setup(self, client):
        res = client.get("/")
        assert res.status_code in (301, 302)
        assert "/setup" in res.headers["Location"]


class TestRunRoute:

    def test_valid_run_returns_battle_id(self, client):
        res = client.post(
            "/run",
            data=json.dumps(VALID_PAYLOAD),
            content_type="application/json",
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "battle_id" in data
        assert "redirect" in data

    def test_missing_army_returns_400(self, client):
        res = client.post(
            "/run",
            data=json.dumps({"army_a": [], "army_b": []}),
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_invalid_json_returns_400(self, client):
        res = client.post("/run", data="not json", content_type="application/json")
        assert res.status_code == 400

    def test_wrong_column_returns_422(self, client):
        bad_payload = {
            "army_a": [
                {"unit_id": "A_B1", "team": "A", "type": "Barbarian",
                 "row": 0, "col": 3,  # col 3 is Team B's zone
                 "move_behavior": "Advance", "attack_behavior": "Closest"},
            ],
            "army_b": VALID_PAYLOAD["army_b"],
        }
        res = client.post(
            "/run",
            data=json.dumps(bad_payload),
            content_type="application/json",
        )
        assert res.status_code == 422

    def test_overlapping_units_returns_422(self, client):
        bad_payload = {
            "army_a": [
                {"unit_id": "A_B1", "team": "A", "type": "Barbarian",
                 "row": 0, "col": 0, "move_behavior": "Advance", "attack_behavior": "Closest"},
                {"unit_id": "A_B2", "team": "A", "type": "Barbarian",
                 "row": 0, "col": 0,  # same cell!
                 "move_behavior": "Advance", "attack_behavior": "Closest"},
            ],
            "army_b": VALID_PAYLOAD["army_b"],
        }
        res = client.post(
            "/run",
            data=json.dumps(bad_payload),
            content_type="application/json",
        )
        assert res.status_code == 422


class TestResultsRoute:

    def _run_and_get_id(self, client):
        res = client.post(
            "/run",
            data=json.dumps(VALID_PAYLOAD),
            content_type="application/json",
        )
        return res.get_json()["battle_id"]

    def test_results_page_loads(self, client):
        battle_id = self._run_and_get_id(client)
        res = client.get(f"/results/{battle_id}")
        assert res.status_code == 200
        assert b"Battle Replay" in res.data

    def test_unknown_battle_returns_404(self, client):
        res = client.get("/results/nonexistent-id")
        assert res.status_code == 404

    def test_download_csv(self, client):
        battle_id = self._run_and_get_id(client)
        res = client.get(f"/download/{battle_id}")
        assert res.status_code == 200
        assert res.content_type == "text/csv; charset=utf-8"
