# ADR-018 Interactive Work Response Builder

## Status

Accepted

## Context

Onecool OS now supports the first Work bridge:

```text
Research Queue READY item
-> Work Request JSON
-> manual ChatGPT Work execution
-> Work Response JSON
-> Work Bridge
-> ORF
-> eBay Sold Evidence Validation
```

The first live workflow exposed a practical usability problem. After manually
verifying eBay Sold comparables, the owner still needs to create a
contract-compliant Work Response JSON. Hand-authoring the envelope and ORF
payload is error-prone, especially for item IDs, dates, prices, warnings,
identity fields, and request IDs.

The system needs a small productivity tool that helps the owner convert manual
research observations into a valid Work Response JSON without changing any
Knowledge Platform behavior.

## Decision

Create an interactive CLI builder:

```bash
.venv/bin/python -m onecool_os build-work-response \
  --request imports/work/kobe_111003720_request.json \
  --output imports/work/kobe_111003720_response.json
```

The builder:

- Reads the existing Work Request JSON.
- Displays asset name, cert number, and research URL.
- Prompts for manually verified eBay Sold comparable fields.
- Produces a Onecool Work Contract v1.0 response envelope.
- Places an ORF-compatible payload inside `outputs.orf_payload`.
- Preserves warnings and uncertainty.
- Writes only the response JSON selected by the user.

The builder does not import the response. The existing Work Bridge remains the
only path from Work Response JSON into ORF and Evidence Validation.

## Boundaries

The builder must not:

- Scrape eBay.
- Call providers.
- Call AI.
- Calculate Fair Value.
- Create ValuationRecord objects.
- Update Portfolio NAV.
- Modify Evidence.
- Modify ORF.
- Modify Runtime.
- Modify Dashboard.
- Generate buy/sell recommendations.

It is a local productivity tool only.

## Output Contract

The builder output follows:

- Onecool Work Contract v1.0 response envelope.
- Onecool Work Response Specification v1.0.
- ORF-compatible `outputs.orf_payload`.

For zero comparables, the builder produces a `NO_MATCH` ORF result rather than
inventing evidence.

For exact matches, the builder marks evidence as completed ORF sold-comparable
evidence and lets existing Evidence Validation classify it.

For non-exact matches, the builder preserves warnings and review status.

## Rationale

This keeps responsibility placement clean:

- ChatGPT Work or the owner performs research.
- The builder formats manually verified observations.
- Work Bridge validates the Work response envelope.
- ORF validates research structure.
- Evidence Validation classifies trust.
- Fair Value, ValuationRecord, NAV, and Dashboard remain downstream and
  untouched.

The builder improves product usability without changing architecture.

## Consequences

Benefits:

- Less manual JSON editing.
- Lower risk of malformed Work responses.
- Faster first live workflow execution.
- Deterministic output from manual inputs.

Tradeoffs:

- Still requires command-line interaction.
- Still depends on owner judgment for manual verification.
- Does not eliminate the need for ORF and Evidence Validation.

## Validation

The builder must be covered by tests for:

- Work Request loading.
- Work Response generation.
- Interactive prompt flow.
- CLI command execution.
- `NO_MATCH` output.
- Existing ORF import compatibility.
- Existing eBay Sold Evidence Validation compatibility.

No production architecture changes are required.
