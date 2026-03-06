"""Locust load-test file for SC-001 performance verification.

Usage (run from repo root with server running on port 8000):
    locust -f locustfile.py --headless -u 50 -r 20 --run-time 60s --host http://localhost:8000

Threshold: ≥95% of requests complete in <5 s (SC-001).
"""
from __future__ import annotations

import uuid

from locust import HttpUser, task


class AuthUser(HttpUser):
    """Simulates a user registering and then logging in."""

    @task
    def register_and_login(self) -> None:
        email = f"loadtest-{uuid.uuid4()}@example.com"
        password = "LoadTestP@ss1"

        self.client.post(
            "/auth/register",
            json={"name": "Load Test User", "email": email, "password": password},
        )
        self.client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
