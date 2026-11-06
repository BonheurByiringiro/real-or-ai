"""
eval_harness.py — Phase 0 evaluation harness.

Two modes:

  python eval_harness.py            (or --validate)
      Offline, free, no API key. Checks that every case bundle is
      well-formed and that its EXPECTED verdicts are reachable under
      the guardrails — e.g. an expected "supported" case must actually
      contain supporting evidence, and an expected high-certainty case
      must have the independent sources the calibration rule demands.
      If a case fails here, the case is wrong, not the model.

  python eval_harness.py --live
      Needs MODEL_API_KEY (Meta Model API, dev.meta.ai). Runs
      VerifierAgent on every case and
      scores it: media-verdict accuracy, claim-verdict accuracy,
      citation validity, and whether "unverified" was used where the
      case expects it. Failures are categorized (doc §15, Phase 0 exit
      criteria: "agent matches published verdicts on most of the set;
      failures categorized").

Failure categories:
  media_wrong       media verdict differs from expected
  claim_wrong       a claim verdict differs from expected
  status_wrong      final/developing differs from expected
  invalid_report    the model's report broke a guardrail (validation)
  agent_error       the API call itself failed
"""

from __future__ import annotations

import sys
from collections import Counter

from cases import CASES, EvalCase
from verifier_agent import (
    ClaimVerdict,
    SourceTier,
    Stance,
    VerifierAgent,
    independent_high_tier_groups,
)


# ---------------------------------------------------------------------------
# Validate mode (offline)
# ---------------------------------------------------------------------------

def check_case_reachable(case: EvalCase) -> list[str]:
    """Is the expected verdict actually justified by the bundle's evidence?"""
    problems: list[str] = []
    bundle = case.bundle
    evidence_by_claim: dict[str, list] = {}
    for item in bundle.evidence:
        evidence_by_claim.setdefault(item.claim_id, []).append(item)

    for claim_id, expected in case.expected_claim_verdicts.items():
        items = evidence_by_claim.get(claim_id, [])
        supporting = [i for i in items if i.stance == Stance.SUPPORTS]
        contradicting = [i for i in items if i.stance == Stance.CONTRADICTS]

        if expected == ClaimVerdict.SUPPORTED and not supporting:
            problems.append(f"{claim_id}: expected SUPPORTED but bundle has no supporting evidence")
        if expected == ClaimVerdict.FALSE and not contradicting:
            problems.append(f"{claim_id}: expected FALSE but bundle has no contradicting evidence")
        if expected == ClaimVerdict.MISLEADING and not (supporting or contradicting):
            problems.append(f"{claim_id}: expected MISLEADING but bundle has no evidence at all")
        if expected == ClaimVerdict.UNVERIFIED and len(independent_high_tier_groups(items)) >= 2:
            problems.append(
                f"{claim_id}: expected UNVERIFIED but bundle already has "
                "2+ independent high-tier sources — is the expectation right?"
            )
    return problems


def run_validate() -> int:
    print(f"Validating {len(CASES)} cases (offline — no model calls)\n")
    bad = 0
    for case in CASES:
        problems = check_case_reachable(case)
        # Round-trip through JSON: proves the bundle survives the exact
        # serialization the agent will receive.
        from verifier_agent import EvidenceBundle
        EvidenceBundle.model_validate_json(case.bundle.model_dump_json())
        if problems:
            bad += 1
            print(f"  FAIL  {case.id}")
            for p in problems:
                print(f"        - {p}")
        else:
            print(f"  ok    {case.id} — {case.description[:70]}")
    print(f"\n{len(CASES) - bad}/{len(CASES)} cases sound and reachable.")
    return 1 if bad else 0


# ---------------------------------------------------------------------------
# Live mode
# ---------------------------------------------------------------------------

def run_live() -> int:
    agent = VerifierAgent()
    print(f"Live eval — model: {agent.model}, {len(CASES)} cases\n")
    failures: Counter = Counter()
    media_right = claim_right = claim_total = 0

    for case in CASES:
        try:
            report = agent.run(case.bundle)
        except Exception as exc:  # API error or guardrail rejection
            kind = "invalid_report" if exc.__class__.__name__ == "ReportValidationError" else "agent_error"
            failures[kind] += 1
            print(f"  {case.id}: {kind} — {exc}")
            continue

        if report.media_verdict == case.expected_media_verdict:
            media_right += 1
        else:
            failures["media_wrong"] += 1
            print(f"  {case.id}: media expected {case.expected_media_verdict.value}, "
                  f"got {report.media_verdict.value}")

        for result in report.claim_results:
            expected = case.expected_claim_verdicts.get(result.claim_id)
            if expected is None:
                continue
            claim_total += 1
            if result.verdict == expected:
                claim_right += 1
            else:
                failures["claim_wrong"] += 1
                print(f"  {case.id}/{result.claim_id}: claim expected {expected.value}, "
                      f"got {result.verdict.value}")

        if report.status != case.expected_status:
            failures["status_wrong"] += 1
            print(f"  {case.id}: status expected {case.expected_status.value}, got {report.status.value}")

    print(f"\nMedia verdicts: {media_right}/{len(CASES)} correct")
    print(f"Claim verdicts: {claim_right}/{claim_total} correct")
    print(f"Failures by category: {dict(failures) if failures else 'none'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(run_live() if "--live" in sys.argv else run_validate())
