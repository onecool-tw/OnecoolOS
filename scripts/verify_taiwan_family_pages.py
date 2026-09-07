#!/usr/bin/env python3
"""Verify publication of existing snapshot bytes. No exporter or signal engines."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen


def verify(expected: bytes, actual: bytes) -> str:
    source, published = json.loads(expected), json.loads(actual)
    for field in ("market_pressure", "market_cta", "top5"):
        if field not in source or published.get(field) != source[field]:
            raise ValueError(f"Snapshot field mismatch: {field}")
    for symbol in ("0050", "2330", "1306", "069500"):
        if symbol not in source["market_cta"]:
            raise ValueError(f"Missing market CTA: {symbol}")
    # List equality above preserves Top 5 order, scores, CTA and every other field.
    if source != published or expected != actual:
        raise ValueError("Published JSON is not byte-identical to formal snapshot")
    return hashlib.sha256(actual).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("published", help="Local staged file or public HTTPS URL")
    parser.add_argument("--source", type=Path, default=Path("data/public/taiwan_stock_family_latest.json"))
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--delay", type=float, default=5)
    args = parser.parse_args()
    expected = args.source.read_bytes()
    if args.attempts < 1 or args.delay < 0:
        parser.error("attempts must be positive and delay nonnegative")
    for attempt in range(args.attempts):
        try:
            if args.published.startswith("https://"):
                request = Request(args.published, headers={"Cache-Control": "no-cache"})
                with urlopen(request, timeout=20) as response:
                    if not response.url.startswith("https://"):
                        raise ValueError("Public endpoint redirected away from HTTPS")
                    actual = response.read()
            else:
                actual = Path(args.published).read_bytes()
            digest = verify(expected, actual)
            print(f"PASS: pressure, Taiwan/Asia CTA, Top 5 order/scores and all bytes match; sha256={digest}")
            return
        except (OSError, ValueError) as exc:
            if attempt + 1 == args.attempts:
                raise
            print(f"Publication not yet verified: {exc}; retrying", flush=True)
            time.sleep(args.delay)


if __name__ == "__main__":
    main()
