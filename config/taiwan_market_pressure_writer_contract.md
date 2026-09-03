# Onecool Taiwan Market Pressure Writer Contract

## Purpose

This contract defines the only supported persistence path for the formal Taiwan market-pressure result produced by the Onecool Taiwan daily Work.

The Work remains the sole evaluator of the pressure light. GitHub does **not** create a second pressure model and consumer Projects must not recompute the light.

## Source of Truth

Formal result location:

`data/market/taiwan_stock_intelligence/daily_context_latest.json.market_pressure`

Formal Work write mailbox:

`data/market/taiwan_stock_intelligence/market_pressure_request_latest.json`

Persistence workflow:

`.github/workflows/persist-taiwan-market-pressure.yml`

Validation / atomic writer:

`scripts/persist_taiwan_market_pressure.py`

## Required Work behavior

After the daily Work completes its normal spot / derivatives / volatility / institutional-flow validation and reaches its formal GREEN / YELLOW / RED judgment, it must update the mailbox file on `main` with that already-evaluated result.

The mailbox update automatically triggers the persistence workflow. The workflow validates the payload, atomically merges it into `daily_context_latest.json.market_pressure`, commits the SSOT, and preserves all other daily-context fields.

Do not ask GitHub to infer the light. Do not create a second set of thresholds in the workflow or writer script.

After the mailbox write, the Work must read back `daily_context_latest.json.market_pressure`. Only when `as_of`, `status`, `light` and `action` agree with the formal result may the Work say the shared SSOT is updated. If the write or read-back verification fails, report `WRITE_FAILED`; do not claim the shared result is current.

## Mailbox payload

The Work writes one JSON object to `market_pressure_request_latest.json`. It should preserve the fixed metadata fields and replace the formal result fields.

Example:

```json
{
  "schema_version": "1.0",
  "module": "Onecool Taiwan Market Pressure Request",
  "as_of": "2026-09-02",
  "status": "CURRENT",
  "light": "RED",
  "reason": [
    "index_selloff",
    "institutional_selling",
    "derivatives_stress"
  ],
  "confirmed_inputs": {
    "spot": true,
    "futures": true,
    "pcr": true,
    "volatility": true,
    "institutional_flow": true,
    "margin": true
  },
  "input_data_as_of": {
    "spot": "2026-09-02",
    "futures": "2026-09-02",
    "pcr": "2026-09-02",
    "volatility": "2026-09-02",
    "institutional_flow": "2026-09-02",
    "margin": "2026-09-01"
  },
  "writer": "FORMAL_TAIWAN_WORK_ONLY"
}
```

The writer derives and validates:

- `action`
- `previous_light`
- `changed`
- `last_change_date`
- `data_quality`

The Work must not fabricate those derived fields.

## Fail-closed rules

- Allowed lights: `GREEN`, `YELLOW`, `RED`, `UNKNOWN`.
- Allowed statuses: `CURRENT`, `STALE_LAST_KNOWN`, `UNKNOWN`.
- `CURRENT` requires a valid `as_of` date and cannot use `UNKNOWN` light.
- `CURRENT + GREEN` requires explicit confirmation of at least spot, futures, PCR, volatility and institutional flow.
- Only `CURRENT + GREEN` receives `ALLOW_EVALUATE_NEW_EXPOSURE`.
- Every other combination receives `PAUSE_NEW_EXPOSURE`.
- News alone never has pressure-light authority.

## Consumer rule

The owner report, wife shared Project, future parent/friend Projects and any other consumer must read `daily_context_latest.json.market_pressure` as the sole formal pressure result. They may explain the formal result with public context, but may not overwrite or recompute it.

All consumers must also use the same Top 5 action-label mapping:

- Stock CTA `BUY` while market pressure is yellow/red or another entry gate is not satisfied: `等待市場轉綠`.
- Stock CTA `HOLD`: `續抱／不新增`.
- Stock CTA `SELL`: `停止新增／覆核`.
- Stock CTA `BUY` with 0050 `BUY`, `CURRENT + GREEN` market pressure, and valid valuation/data gates: `評估新增`.
- Stock CTA `UNKNOWN` or unusable stale/anomalous data: `資料待確認／不新增`.

This is a presentation contract only. It must not modify CTA values, scores, valuation, ranking, or the formal pressure light.

## Smoke-test status

The mailbox → GitHub Actions → validator → `daily_context_latest.json.market_pressure` path was smoke-tested successfully on 2026-09-02. Until the first formal Work write arrives, the SSOT remains `UNKNOWN` and `PAUSE_NEW_EXPOSURE` by design.
