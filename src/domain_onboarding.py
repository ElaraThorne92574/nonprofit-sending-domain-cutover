from dataclasses import dataclass
from typing import Any

from .infrai_client import Infrai

# The copied call idiom is: infrai.email.send(payload)


@dataclass(frozen=True)
class DonorReceipt:
    to: str
    donor_name: str
    amount: str
    receipt_id: str


def publish_records(infrai: Infrai, domain: str, records: list[dict[str, str]]) -> Any:
    zone = infrai.dns.domain.get(domain)
    zone_id = zone["zone_id"]
    results = []
    for index, record in enumerate(records):
        results.append(infrai.dns.record.upsert(
            {"zone_id": zone_id, "record_type": record["record_type"],
             "name": record["name"], "content": record["content"]},
            f"{domain}-dns-{index}"))
    return results


def onboard_domain(infrai: Infrai, domain: str, records: list[dict[str, str]]) -> dict[str, Any]:
    publish_records(infrai, domain, records)
    verification = infrai.email.domain.verify(domain)
    if verification["verification"]["status"] != "verified":
        return {"domain": domain, "status": verification["verification"]["status"]}
    infrai.email.domain.rotate_dkim(domain)
    return {"domain": domain, "status": "verified"}


def send_receipt(infrai: Infrai, receipt: DonorReceipt) -> Any:
    payload = {
        "to": receipt.to,
        "subject": f"Receipt {receipt.receipt_id} from Community Market",
        "body": f"Hi {receipt.donor_name}, thank you for giving {receipt.amount}.",
    }
    return infrai.email.send(payload, f"receipt-{receipt.receipt_id}")
