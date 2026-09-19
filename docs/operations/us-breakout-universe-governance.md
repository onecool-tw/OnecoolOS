# US Breakout Universe Governance

## Purpose

The Onecool US breakout universe is a versioned research universe, not a daily
momentum list. Stable membership keeps historical scans reproducible while the
daily validation and scoring layers determine which members are eligible for
that day's ranking.

## Current mandate

- Target size: 70 securities.
- Eligible instruments: US-listed common stocks, ADRs, and foreign ordinary
  shares with an explicit ticker, company-name, and security-type mapping.
- Mandate: liquid US market leaders and research-relevant leadership candidates
  across technology, semiconductors, communications, consumer, financials,
  industrials, healthcare, energy, and selected cross-listed leaders.
- Daily membership mutation: prohibited.
- Daily ranking eligibility is separate from universe membership.

## Admission requirements

A new member must pass all hard requirements at the proposed effective date:

1. identity and security type are explicitly mapped;
2. at least 252 aligned daily observations are available;
3. latest data uses the same completed US session and adjusted-close basis as
   SPY;
4. OHLCV is positive, ordered, unique, and internally consistent;
5. 50-day average dollar volume is at least USD 20 million;
6. fundamentals required by the active scoring version are source-traceable and
   pass their point-in-time cutoff;
7. the security is not under a confirmed delisting, completed merger, or ticker
   retirement.

Admission also requires a documented leadership rationale. At least one must be
supported: CANSLIM proxy pass, Minervini proxy pass, positive 126-session
relative strength versus SPY, or verified industry leadership. A screen result
is research prioritization, not an investment recommendation.

## Scheduled review

Review membership after the final completed US session of each calendar quarter.
The review may recommend changes, but no change becomes effective without:

- a proposed add and remove list;
- evidence for every hard requirement;
- a reason for each addition and removal;
- confirmation that the target size remains 70, unless a separately approved
  mandate change says otherwise;
- an updated universe version;
- tests and an auditable pull request or commit.

Short-term price weakness, a single failed daily fetch, a temporary score
decline, or one quarter of below-threshold liquidity does not cause automatic
removal. Two consecutive quarterly failures of a hard operating requirement
trigger replacement review.

## Emergency review

An immediate review is allowed only for:

- delisting or trading termination;
- completed merger or retired ticker;
- invalidated identity or security type.

The replacement must still pass the admission requirements. No unverified
symbol may be inserted to preserve the target count.

## Reporting language

When assessment is complete, report:

> Candidate universe 70/70 assessed; X eligible for scoring and Y
> rule-excluded.

Do not describe rule-excluded securities as unvalidated or missing coverage.
Report true data-validation failures separately with exact symbols and causes.

## Version record

| Version | Effective/review date | Target size | Notes |
|---|---:|---:|---|
| 2026Q3-v1 | 2026-08-21 | 70 | Initial versioned liquid US leadership universe |

Next scheduled review: 2026-09-30 after the completed US session.
