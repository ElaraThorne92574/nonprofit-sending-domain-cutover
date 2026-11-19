from src.domain_onboarding import onboard_domain


class FakeEmail:
    def __init__(self):
        self.rotated = False
        self.domain = self

    def verify(self, domain):
        return {"verification": {"status": "verified"}}

    def rotate_dkim(self, domain):
        self.rotated = True


class FakeDns:
    def __init__(self):
        self.records = []
        self.domain = self
        self.record = self

    def get(self, domain):
        return {"zone_id": "zone-7"}

    def upsert(self, record, request_id):
        self.records.append((record, request_id))


class FakeInfrai:
    def __init__(self):
        self.email = FakeEmail()
        self.dns = FakeDns()


def test_verified_domain_writes_records_then_rotates_dkim():
    api = FakeInfrai()
    result = onboard_domain(api, "give.example", [
        {"record_type": "TXT", "name": "give.example", "content": "v=spf1 include:mail.example ~all"},
        {"record_type": "TXT", "name": "_dmarc.give.example", "content": "v=DMARC1; p=none"},
    ])
    assert result == {"domain": "give.example", "status": "verified"}
    assert api.dns.records[0][0]["zone_id"] == "zone-7"
    assert api.email.rotated is True
