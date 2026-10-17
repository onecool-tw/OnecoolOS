# Fund NAV backup acquisition

Anue NavHIS remains the primary. On a primary read/validation failure only,
MoneyDJ public NAV pages may append verified observations. Reports still read
only the latest committed main cache and use the existing shared CTA/Action
engine. No proxy substitution or return estimation is permitted.

## Explicit USD share classes

| Onecool | MoneyDJ | Share class |
|---|---|---|
| A10124 | ACFP111 | Fubon AI A USD, not N |
| A16075 | ACCA74 | Capital India Small/Mid USD, not N or TWD |
| B23554 | PYZQ4 | Schroder Global Gold A USD accumulation |
| B15080 | FLZ81 | Franklin Biotechnology Discovery A(acc) USD |
| B09007 | SHZ19 | BlackRock World Mining A2 USD |
| B16019 | ISZ04 | Invesco Global Consumer Trends A USD accumulation |
| B23070 | PYZE3 | Schroder Global Energy A1 USD accumulation |

Public URLs use `https://www.moneydj.com/funddj/ya/yp010000.djhtm?a=CODE`
for the two Taiwan funds and `yp010001.djhtm` for the five offshore funds.

## Acceptance gate

- Check exact mapped identity in the document title, including share class and
  USD currency. Fail on redirects, missing/invalid dates or values.
- Anchor MM/DD observations to the explicit YYYY/MM/DD NAV header. Handle
  December/January from that anchor; reject future/duplicate/out-of-window rows.
- Require at least eight overlapping actual NAV dates, including the existing
  latest date. Check every available overlap within absolute 0.00005 NAV units
  (four-decimal page rounding). Any larger discrepancy is CONFLICT, not averaged.
- Append only dates after the verified baseline; never overwrite an old NAV.
  A stale backup behind the baseline or insufficient overlap is rejected.
- Store each fallback's source URL, document SHA-256, fetched time, effective
  source date, overlap count and appended count in per-fund `nav_refresh.backup`.
  Preserve the primary error separately. A successful fallback is an actual
  provider read; no newer NAV remains NO_NEW_NAV with the real valuation date.
- If both providers fail, retain the dated history. The existing all-seven
  failure publication guard remains active. Normal scheduled recovery continues.

## Initial live validation — 2026-10-17

All seven mapped pages were reachable. Each had 29–30 matching observations
against committed Anue history. Five had one newer observation; Gold and Energy
had no newer NAV. This validates the acquisition mappings, not a promise of
continuous availability. Website schema changes must fail closed.
