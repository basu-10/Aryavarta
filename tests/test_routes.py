"""tests/test_routes.py — Flask route tests using the test client."""

import json
import uuid
import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from db import models as m


@pytest.fixture
def client(tmp_path):
    app = create_app(output_dir=str(tmp_path))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


VALID_PAYLOAD = {
    "army_a": [
        {"unit_id": "A_B1", "team": "A", "type": "Barbarian", "row": 0, "col": 1},
        {"unit_id": "A_B2", "team": "A", "type": "Barbarian", "row": 1, "col": 2},
    ],
    "army_b": [
        {"unit_id": "B_AR1", "team": "B", "type": "Archer", "row": 0, "col": 8},
        {"unit_id": "B_AR2", "team": "B", "type": "Archer", "row": 1, "col": 7},
    ],
}


class TestSetupRoute:

    def test_get_setup(self, client):
        res = client.get("/setup")
        assert res.status_code == 200
        assert b"Battle Simulator" in res.data

    def test_root_loads_landing_for_guest(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert b"BattleCells" in res.data

    def test_root_redirects_logged_in_user_to_world(self, client):
        with client.session_transaction() as sess:
            sess["player_id"] = 1
            sess["username"] = "demo"

        res = client.get("/")
        assert res.status_code in (301, 302)
        assert "/world" in res.headers["Location"]


class TestRememberAuth:

    def _create_user(self, client, username: str | None = None, password: str = "pw123"):
        username = username or f"u_{uuid.uuid4().hex[:8]}"
        with client.application.app_context():
            world_id = m.create_world(f"w_{uuid.uuid4().hex[:8]}", 10, 10, 0, 0)
            player_id = m.create_player(username, generate_password_hash(password))
            m.create_castle(player_id, 4, 0, 0, world_id)
        return username, password

    def test_remember_cookie_restores_session_after_session_clear(self, client):
        username, password = self._create_user(client)

        login_res = client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=False,
        )
        assert login_res.status_code in (301, 302)
        assert "bc_remember=" in (login_res.headers.get("Set-Cookie") or "")

        with client.session_transaction() as sess:
            sess.clear()

        restored = client.get("/api/dm/unread")
        assert restored.status_code == 200
        assert "unread" in restored.get_json()

    def test_logout_revokes_remember_cookie(self, client):
        username, password = self._create_user(client)

        client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=False,
        )

        client.get("/logout", follow_redirects=False)

        with client.session_transaction() as sess:
            sess.clear()

        res = client.get("/api/dm/unread", follow_redirects=False)
        assert res.status_code in (301, 302)
        assert "/login" in res.headers.get("Location", "")


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
                 "row": 0, "col": 5},  # col 5 is Team B's zone
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
                 "row": 0, "col": 1},
                {"unit_id": "A_B2", "team": "A", "type": "Barbarian",
                 "row": 0, "col": 1},  # same cell!
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
