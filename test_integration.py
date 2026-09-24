"""Acceptance scenario 1 against a running relay (real API and database).

Set RELAY_BASE_URL (e.g. http://127.0.0.1:8000) to run; skipped otherwise.
"""

import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("RELAY_BASE_URL", "")

pytestmark = pytest.mark.skipif(not BASE_URL, reason="RELAY_BASE_URL is not set")


def register(client: httpx.Client, name: str) -> tuple[str, dict[str, str]]:
    response = client.post("/api/v1/agents", json={"name": name})
    assert response.status_code == 201
    data = response.json()
    return data["agent_id"], {"Authorization": f"Bearer {data['token']}"}


def test_two_agents_exchange_task_and_result():
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        assert client.get("/ready").status_code == 200
        _sender_id, sender = register(client, "it-sender")
        recipient_id, recipient = register(client, "it-uppercase")
        payload = f"hello relay {uuid.uuid4().hex[:8]}"

        sent = client.post("/api/v1/tasks", headers=sender, json={"to": recipient_id, "input": payload})
        assert sent.status_code == 201
        assert sent.json()["status"] == "queued"
        task_id = sent.json()["task_id"]

        claim = client.post(
            "/api/v1/tasks/claim", headers=recipient, json={"worker_id": "it-worker", "wait_seconds": 5}
        )
        assert claim.status_code == 200
        claimed = claim.json()
        assert claimed["task_id"] == task_id
        assert claimed["input"] == payload
        assert client.get(f"/api/v1/tasks/{task_id}", headers=sender).json()["status"] == "processing"

        done = client.post(
            f"/api/v1/tasks/{task_id}/complete",
            headers=recipient,
            json={"claim_token": claimed["claim_token"], "output": payload.upper()},
        )
        assert done.status_code == 200

        result = client.get(f"/api/v1/tasks/{task_id}", headers=sender).json()
        assert result["status"] == "completed"
        assert result["output"] == payload.upper()
        assert result["attempt_count"] == 1

        attempts = client.get(f"/api/v1/tasks/{task_id}/attempts", headers=sender).json()["items"]
        assert [a["outcome"] for a in attempts] == ["completed"]
        assert all("claim_token" not in a for a in attempts)
