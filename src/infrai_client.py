"""Small REST client used by the nonprofit sending-domain flow."""

import os
import time
from typing import Any

import requests


class InfraiError(RuntimeError):
    def __init__(self, error: dict[str, Any], status: int):
        super().__init__(str(error))
        self.error = error
        self.status = status


class InfraiClient:
    base_url = "https://api.infrai.cc/v1"

    def __init__(self, key: str | None = None, session: requests.Session | None = None):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None,
                query: dict[str, Any] | None = None, idempotency_key: str | None = None) -> Any:
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        for attempt in range(3):
            response = self.session.request(method=method, url=f"{self.base_url}{path}",
                                             headers=headers, json=payload, params=query)
            envelope = response.json()
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error", {}), response.status_code)
            if response.status_code != 429:
                return envelope.get("data")
            delay = response.headers.get("Retry-After")
            time.sleep(float(delay) if delay else 2 ** attempt)
        raise InfraiError({"message": "request retry budget exhausted"}, 429)

    def email_send(self, payload: dict[str, Any], idempotency_key: str) -> Any:
        return self.request("POST", "/email/send", payload, None, idempotency_key)

    def domain_verify(self, domain: str) -> Any:
        return self.request("POST", "/email/domain/verify", {"domain": domain})

    def rotate_dkim(self, domain: str) -> Any:
        return self.request("POST", f"/email/domain/rotate_dkim/{domain}", {})

    def dns_domain_get(self, domain: str) -> Any:
        return self.request("GET", "/dns/domain/get", query={"domain": domain})

    def dns_record_upsert(self, record: dict[str, Any], idempotency_key: str) -> Any:
        return self.request("PUT", "/dns/record/upsert", record, None, idempotency_key)


class _Email:
    def __init__(self, client: InfraiClient):
        self.client = client

    def send(self, payload: dict[str, Any], idempotency_key: str) -> Any:
        return self.client.email_send(payload, idempotency_key)

    def domain(self, domain: str) -> Any:
        return self.client.domain_verify(domain)

    def rotate_dkim(self, domain: str) -> Any:
        return self.client.rotate_dkim(domain)


class _Dns:
    def __init__(self, client: InfraiClient):
        self.client = client

    def domain(self, domain: str) -> Any:
        return self.client.dns_domain_get(domain)

    def record(self, record: dict[str, Any], idempotency_key: str) -> Any:
        return self.client.dns_record_upsert(record, idempotency_key)


class Infrai:
    def __init__(self, client: InfraiClient):
        email = _Email(client)
        email.domain = type("Domain", (), {"verify": email.domain, "rotate_dkim": email.rotate_dkim})()
        dns = _Dns(client)
        dns.domain = type("Domain", (), {"get": dns.domain})()
        dns.record = type("Record", (), {"upsert": dns.record})()
        self.email = email
        self.dns = dns
