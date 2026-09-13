# Report delivery contract v1

Market-data health and report delivery are independent. `report_delivery` lists the
latest reporting window whose scheduled start plus two hours has passed, using
Asia/Taipei. `end_to_end_status` is READY only if both layers are ready.
Missing, stale or unverifiable receipts never imply delivery. The monitor does
not send reports or retry email, so it cannot duplicate deliveries.

After each authorized report run, write a sanitized receipt to
`data/operations/report_delivery/{report_id}/{YYYY-MM-DD}.json` on main.
Report IDs: `taiwan`, `us`, `fund`, `cards`, `home`. Date is the scheduled report
window date in Taipei, not the market-data date. Preserve existing delivery
instructions and deduplication. Do not create new recipients or channels.

```json
{
  "report_id": "taiwan",
  "report_date": "2026-09-14",
  "generated_at": "2026-09-14T18:25:00+08:00",
  "delivery_status": "PREPARED",
  "writeback_status": "UNKNOWN",
  "delivery_evidence_sha256": null
}
```

Allowed delivery states: PREPARED, DELIVERED, FAILED, UNKNOWN. DELIVERED requires
positive API acknowledgement for every delivery required by the existing task,
plus VERIFIED report artifact writeback/readback. Hash the private acknowledgement
with SHA-256; retain the original evidence privately. Never put recipients,
message IDs, report contents, holdings, property addresses or credentials in this
public receipt. A prepared conversation response alone is not acknowledgement.
Receipt write failure must be reported explicitly. Never fabricate old receipts.
A digest provides an audit reference, not independent verification of the provider;
the reporting task remains responsible for checking the underlying evidence.

Current schedules: Taiwan Mon–Fri 18:00; US Tue–Sat 16:00; fund Mon–Sat 11:30;
cards Saturday 07:00; home days 2/12/22 08:00. Update the monitor when schedules change.
