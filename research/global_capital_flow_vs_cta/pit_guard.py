"""Research-only PIT guards. Never imported by production CTA."""
import csv
from collections import defaultdict
from datetime import date, datetime, timezone
from math import isfinite

FACTORS = frozenset({"WALCL", "BAMLH0A0HYM2"})
REQUIRED = {"factor", "observation_date", "available_at_utc", "value", "vintage_id", "source_url", "evidence_id"}

def load_verified_vintages(path):
    """Require verifiable source identifiers; do not infer release timestamps."""
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError("PIT release-time and evidence contract absent")
        found, seen = defaultdict(list), set()
        for row in reader:
            factor = row["factor"].strip()
            if factor not in FACTORS:
                raise ValueError("unapproved factor")
            if any(not row[k].strip() for k in ("vintage_id", "source_url", "evidence_id")):
                raise ValueError("missing vintage or source evidence")
            if not row["source_url"].startswith("https://"):
                raise ValueError("source URL must use HTTPS")
            obs = date.fromisoformat(row["observation_date"])
            released = datetime.fromisoformat(row["available_at_utc"].replace("Z", "+00:00"))
            if released.utcoffset() is None or released.utcoffset().total_seconds() != 0:
                raise ValueError("explicit UTC release timestamp required")
            if released.date() < obs:
                raise ValueError("release predates observation")
            value = float(row["value"])
            if not isfinite(value):
                raise ValueError("nonfinite observation")
            identity = (factor, obs, released, row["vintage_id"])
            if identity in seen:
                raise ValueError("duplicate vintage identity")
            seen.add(identity)
            found[factor].append((released, obs, value, row["vintage_id"]))
    if set(found) != FACTORS:
        raise ValueError("both factor histories required")
    for factor in FACTORS:
        found[factor].sort()
    return found

def visible_as_of(vintages, factor, cutoff):
    if cutoff.tzinfo is None:
        raise ValueError("decision cutoff must be timezone aware")
    cutoff = cutoff.astimezone(timezone.utc)
    versions = {}
    for released, observation, value, vintage in vintages.get(factor, ()):
        if released <= cutoff and (observation not in versions or released > versions[observation][0]):
            versions[observation] = (released, observation, value, vintage)
    return [versions[key] for key in sorted(versions)]

def require_common_sample(sessions, minimum=252):
    if len(sessions) < minimum or sessions != sorted(set(sessions)):
        raise ValueError("invalid or insufficient common sample: no publishable performance")
    return sessions[0], sessions[-1]
