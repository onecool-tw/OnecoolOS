# Onecool Taiwan Market Pressure Writer Contract

## Purpose

This contract defines the only supported persistence path for the formal Taiwan
market-pressure result produced by the Onecool Taiwan daily Work.

The Work remains the sole evaluator of the pressure light. GitHub does **not**
create a second pressure model and consumer Projects must not recompute the light.

## Source of Truth

Formal result location:

`data/market/taiwan_stock_intelligence/daily_context_latest.json.market_pressure`

Persistence workflow:

`.github/workflows/persist-taiwan-market-pressure.yml`

Validation / atomic writer:

`scripts/persist_taiwan_market_pressure.py`

## Required Work behavior

After the daily Work has completed its normal spot / derivatives / volatility /
institutional-flow validation and has reached its formal GREEN / YELLOW / RED
judgment, it must persist that already-evaluated result through the persistence
workflow before treating the shared SSOT as updated.

Do not ask GitHub to infer the light. Do not create a second set of thresholds in
the workflow or writer script.

If persistence fails, the Work must say that the formal pressure write-back failed.
It must not claim that `daily_context_latest.json` has been updated. Existing
consumers continue to use the last verifiable persisted result, subject to its
status/date rules.

## workflow_dispatch input

The workflow accepts one required string input named `payload_json`.

Example:

```json
{
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
  }
}
```

The writer derives and validates:

- `action`
- `previous_light`
- `changed`
- `last_change_date`
- `data_quality`

The Work should not fabricate those derived fields.

## Fail-closed rules

- Allowed lights: `GREEN`, `YELLOW`, `RED`, `UNKNOWN`.
- Allowed statuses: `CURRENT`, `STALE_LAST_KNOWN`, `UNKNOWN`.
- `CURRENT` requires a valid `as_of` date and cannot use `UNKNOWN` light.
- `CURRENT + GREEN` requires explicit confirmation of at least spot, futures,
  PCR, volatility and institutional flow.
- Only `CURRENT + GREEN` receives `ALLOW_EVALUATE_NEW_EXPOSURE`.
- Every other combination receives `PAUSE_NEW_EXPOSURE`.
- News alone never has pressure-light authority.

## Consumer rule

The owner report, wife shared Project, future parent/friend Projects and any other
consumer must read `daily_context_latest.json.market_pressure` as the sole formal
pressure result. They may explain the formal result with public context, but may
not overwrite or recompute it.
