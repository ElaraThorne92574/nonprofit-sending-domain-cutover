import os

from .domain_onboarding import DonorReceipt, onboard_domain, send_receipt
from .infrai_client import Infrai, InfraiClient


def main() -> None:
    client = Infrai(InfraiClient())
    domain = os.environ["SENDING_DOMAIN"]
    print(onboard_domain(client, domain, [
        {"record_type": "TXT", "name": domain, "content": os.environ["SPF_CONTENT"]},
        {"record_type": "TXT", "name": f"_dmarc.{domain}", "content": os.environ["DMARC_CONTENT"]},
    ]))
    print(send_receipt(client, DonorReceipt(os.environ["DEMO_EMAIL_TO"], "Sam", "$25", "receipt-1001")))


if __name__ == "__main__":
    main()

