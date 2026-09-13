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

## Per-channel evidence (v2)

Receipts may include `channels`, mapping `conversation` and (for Taiwan) `email`
to `{status, observed_at, evidence_sha256}`. DELIVERED requires a real observed
message/provider acknowledgement; `observed_at` is timezone-aware and within the
reporting window. A successful email does not establish conversation delivery.
The monitor verifies each required channel independently and returns PARTIAL if
only some channels are proven. Report writeback must also be VERIFIED before
all-channel DELIVERED. If the reporting executor cannot observe its own final
conversation delivery, keep that channel UNKNOWN; a subsequent authorized audit
may add evidence after observing the actual delivered message. Never substitute
a last-run timestamp or a prepared draft for delivery evidence. Historical
receipts may be added only after real source verification, never inferred.

Receipt commits trigger health evaluation immediately through GitHub Actions.

An optional `artifact` channel records actual saved report readback independently.
It can establish PARTIAL delivery but never substitutes for conversation/email.
Recovery artifacts must identify their creation date and reconstruction scope;
they do not establish on-time delivery of a historical report.
