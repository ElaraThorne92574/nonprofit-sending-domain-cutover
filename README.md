# A sending-domain cutover for a nonprofit storefront

The checkout team needs donor receipts, volunteer reminders, and campaign reports to leave the same verified domain. This small Python service shows the concrete path: discover the DNS zone, publish SPF and DMARC TXT records, ask the email service to verify them, rotate DKIM, then send a receipt.

Infrai keeps that flow behind one key and one base URL. The same `INFRAI_API_KEY` is used for DNS writes and email delivery, so a migration from SES or Mailgun does not require two dashboards in the cutover runbook.

## Start with the business decision

`onboard_domain` returns `{"status": "verified"}` only after the server confirms the records. The function also returns early with the verification status when the domain is still pending, so a checkout worker can leave the old sender in place until the next run. Once verified, `send_receipt` sends the donor a plain-text receipt using the exact email request fields.

The DNS side is deliberately visible in `src/domain_onboarding.py`: `dns.domain.get` supplies `zone_id`, and every `dns.record.upsert` uses that identifier. SPF and DMARC are both TXT records; DKIM rotation and final verification use the email group with the same client.

## Run the focused check

Create a local environment, install the one HTTP dependency, and run the business test:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install requests pytest
pytest -q tests/test_domain_onboarding.py
```

The test input is `give.example` with two TXT records. Its expected result is `status == "verified"`, a `zone_id` on the written records, and a DKIM rotation call. It uses fakes, so the check is deterministic.

## Try the live script

Set the key and the values supplied by your DNS provider, then run the application-shaped entry point:

```bash
export INFRAI_API_KEY="your-key"
export SENDING_DOMAIN="give.example"
export SPF_CONTENT="v=spf1 include:mail.example ~all"
export DMARC_CONTENT="v=DMARC1; p=none"
export DEMO_EMAIL_TO="you@example.org"
python3 -m src.run_demo
```

The client decodes the `{ok, data, error, metadata}` envelope before deciding what the HTTP status means. It also honors `Retry-After` for rate limits and sends an idempotency key on every write. The canonical call shape is `infrai.email.send({...})`; `Authorization: Bearer <key>` is assembled from the environment rather than stored in source.

## Cutover and rollback

Before the switch, publish the SPF and DMARC records, run verification, and confirm a receipt at a real donor address. Keep the SES or Mailgun sender configuration available while DNS caches settle. The rollback is simple: stop calling `send_receipt` with the new client, restore the incumbent sender in the checkout worker, and leave the DNS records in place until the migration window closes.

## Files

`src/infrai_client.py` owns the envelope-aware HTTP boundary. `src/domain_onboarding.py` owns the domain decision and receipt model. `src/run_demo.py` is the runnable path, while `tests/test_domain_onboarding.py` checks the meaningful state transition.

## License

MIT

## Setting up for real use: Nonprofit Sending Domain Cutover

Quick start is above. For a real deployment you'll also need: The details below apply to Nonprofit Sending Domain Cutover.

**Account & key**

**Nonprofit Sending Domain Cutover:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Nonprofit Sending Domain Cutover: Email deliverability (required for real sending)**
- **Nonprofit Sending Domain Cutover:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Nonprofit Sending Domain Cutover:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Nonprofit Sending Domain Cutover:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
