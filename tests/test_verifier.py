"""
Offline tests for verifier_agent — no API key, no cost, no network.

The runner is tested with a FAKE Meta Model API client that returns
canned function calls. That is the pattern to reuse whenever we test
LLM code: inject the client, never call the real API in a test.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cases import CASES, CASES_BY_ID
from eval_harness import check_case_reachable
from verifier_agent import (
    SYSTEM_PROMPT,
    ClaimResult,
    ClaimVerdict,
    MediaVerdict,
    Report,
    ReportStatus,
    ReportValidationError,
    VerifierAgent,
    validate_report,
)


# --- the cases themselves ---------------------------------------------------

def test_all_cases_are_reachable():
    for case in CASES:
        assert check_case_reachable(case) == [], case.id


def test_case_count_and_unique_ids():
    assert len(CASES) >= 8
    assert len({c.id for c in CASES}) == len(CASES)


# --- guardrails ---------------------------------------------------------------

def _good_report(bundle, **overrides) -> Report:
    """A minimal correct report for the Roadster case."""
    data = dict(
        submission_id=bundle.submission_id,
        media_verdict=MediaVerdict.AUTHENTIC,
        media_confidence=0.8,
        media_reasoning="Official and wire evidence confirm the event; detector score is one weak signal.",
        claim_results=[ClaimResult(
            claim_id="c1", verdict=ClaimVerdict.SUPPORTED, confidence=0.8,
            supporting_evidence_ids=["e1", "e2"], contradicting_evidence_ids=[],
            reasoning="Primary source and wire report support the claim.")],
        status=ReportStatus.FINAL,
        summary="Real footage, true claim",
    )
    data.update(overrides)
    return Report(**data)


def test_valid_report_passes():
    bundle = CASES_BY_ID["roadster_real_event"].bundle
    assert validate_report(bundle, _good_report(bundle)) == []


def test_invented_evidence_id_is_rejected():
    bundle = CASES_BY_ID["roadster_real_event"].bundle
    report = _good_report(bundle)
    report.claim_results[0].supporting_evidence_ids = ["e1", "e999"]
    errors = validate_report(bundle, report)
    assert any("not in the bundle" in e for e in errors)


def test_supported_without_citations_is_rejected():
    bundle = CASES_BY_ID["roadster_real_event"].bundle
    report = _good_report(bundle)
    report.claim_results[0].supporting_evidence_ids = []
    errors = validate_report(bundle, report)
    assert any("no supporting evidence" in e for e in errors)


def test_evidence_from_wrong_claim_is_rejected():
    bundle = CASES_BY_ID["roadster_real_event"].bundle
    report = _good_report(bundle)
    # e1 belongs to c1; cite it for a claim that does not exist in the bundle.
    report.claim_results[0].claim_id = "cX"
    errors = validate_report(bundle, report)
    assert errors  # unknown claim


def test_overconfidence_is_rejected():
    """0.95 confidence on one low-tier blog must fail calibration."""
    bundle = CASES_BY_ID["breaking_news_unverified"].bundle
    report = Report(
        submission_id=bundle.submission_id,
        media_verdict=MediaVerdict.UNKNOWN, media_confidence=0.5,
        media_reasoning="No media to judge.",
        claim_results=[ClaimResult(
            claim_id="c1", verdict=ClaimVerdict.SUPPORTED, confidence=0.95,
            supporting_evidence_ids=["e1"], contradicting_evidence_ids=[],
            reasoning="The blog says so.")],
        status=ReportStatus.FINAL, summary="Trust me",
    )
    errors = validate_report(bundle, report)
    assert any("0.9" in e for e in errors)


def test_syndicated_copies_count_once():
    """Roadster e2+e3 share one independence group; citing both plus e1 is
    two independent sources — but e2+e3 alone would be only one."""
    bundle = CASES_BY_ID["roadster_real_event"].bundle
    report = _good_report(bundle)
    report.claim_results[0].supporting_evidence_ids = ["e2", "e3"]
    report.claim_results[0].confidence = 0.95
    errors = validate_report(bundle, report)
    assert any("independent" in e for e in errors)


# --- the prompt ---------------------------------------------------------------

def test_prompt_contains_the_core_rules():
    for phrase in ["EVIDENCE-ONLY", "TWO VERDICTS", "INDEPENDENCE COUNTS ONCE",
                   "ABSENCE IS NOT FALSITY", "CALIBRATION"]:
        assert phrase in SYSTEM_PROMPT


# --- the runner, with a fake client --------------------------------------------

class FakeResponses:
    """Stands in for the Meta Model API Responses endpoint (openai SDK shape)."""

    def __init__(self, report_dict):
        self._report_dict = report_dict
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        item = SimpleNamespace(type="function_call", name="submit_report",
                               arguments=json.dumps(self._report_dict))
        return SimpleNamespace(output=[item])


def _fake_agent(report_dict):
    client = SimpleNamespace(responses=FakeResponses(report_dict))
    return VerifierAgent(client=client, model="muse-spark-1.3")


def test_runner_returns_validated_report():
    bundle = CASES_BY_ID["roadster_real_event"].bundle
    report_dict = _good_report(bundle).model_dump(mode="json")
    report = _fake_agent(report_dict).run(bundle)
    assert report.media_verdict == MediaVerdict.AUTHENTIC
    assert report.claim_results[0].verdict == ClaimVerdict.SUPPORTED


def test_runner_rejects_invented_citation():
    bundle = CASES_BY_ID["roadster_real_event"].bundle
    report_dict = _good_report(bundle).model_dump(mode="json")
    report_dict["claim_results"][0]["supporting_evidence_ids"] = ["nope"]
    with pytest.raises(ReportValidationError):
        _fake_agent(report_dict).run(bundle)


def test_missing_api_key_gives_a_helpful_error(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="MODEL_API_KEY"):
        _ = VerifierAgent().client


def test_runner_forces_the_report_function_first():
    bundle = CASES_BY_ID["roadster_real_event"].bundle
    agent = _fake_agent(_good_report(bundle).model_dump(mode="json"))
    agent.run(bundle)
    first_call = agent.client.responses.calls[0]
    assert first_call["tool_choice"] == {"type": "function", "name": "submit_report"}
    assert first_call["tools"][0]["name"] == "submit_report"
    assert first_call["model"] == "muse-spark-1.3"
