"""
cases.py — hand-built evaluation cases for Phase 0.

Each case is an EvidenceBundle (exactly what the reasoning agent will
see in production, minus the parts Phases 1-2 will automate) plus the
verdicts a correct agent should reach.

The cases are teaching cases: patterns modeled on the design doc's
examples and on common fact-check patterns, with evidence summaries
written in our own words. They are NOT scraped live fact-checks — in
Phase 1 we replace/augment them with real published fact-checks
(20-30 per the doc's exit criteria).

The 8 patterns, on purpose:
  1. real-but-strange event      detectors cry "AI", evidence says real
  2. real footage, false caption media authentic, claim false
  3. synthetic media, true claim media synthetic, claim supported
  4. AI product that doesn't exist  media synthetic, claim false
  5. breaking news, thin coverage   claim unverified, status developing
  6. spliced real clips             media edited, claim misleading
  7. satire shared as news          claim misleading
  8. plain supported story          the control case — everything agrees
"""

from __future__ import annotations

from dataclasses import dataclass, field

from verifier_agent import (
    C2PAStatus,
    Claim,
    ClaimVerdict,
    DetectorScore,
    EvidenceBundle,
    EvidenceItem,
    MediaSignals,
    MediaVerdict,
    ReportStatus,
    SourceTier,
    Stance,
    SubmissionType,
)


@dataclass
class EvalCase:
    id: str
    description: str
    bundle: EvidenceBundle
    expected_media_verdict: MediaVerdict
    expected_claim_verdicts: dict[str, ClaimVerdict]
    expected_status: ReportStatus = ReportStatus.FINAL


def _ev(id, claim_id, publisher, tier, group, stance, summary, url="https://example.org/item", date="2026-10-20"):
    return EvidenceItem(id=id, claim_id=claim_id, url=url, publisher=publisher,
                        tier=tier, published_at=date, summary=summary,
                        independence_group=group, stance=stance)


CASES: list[EvalCase] = [

    # 1 — Real but strange (the doc's Tesla Roadster pattern)
    EvalCase(
        id="roadster_real_event",
        description="Flying-car demo footage looks fake; detector is suspicious; "
                    "official + wire coverage confirms the event happened.",
        bundle=EvidenceBundle(
            submission_id="sub-001", submission_type=SubmissionType.VIDEO,
            caption="Tesla Roadster flying demo, October 15 — is this real??",
            current_date="2026-10-30",
            claims=[Claim(id="c1", text="Tesla demonstrated a flying Roadster on October 15, 2026.",
                          normalized_text="Tesla demonstrated a flying Roadster on 2026-10-15.",
                          entities=["Tesla", "Roadster"])],
            media_signals=MediaSignals(
                c2pa_status=C2PAStatus.ABSENT,
                detector_scores=[DetectorScore(name="clip-vit-ensemble", score=0.62,
                                               note="Unusual motion reads as synthetic")],
                first_seen_at="2026-10-15", original_uploader="@event attendee account"),
            evidence=[
                _ev("e1", "c1", "Tesla Newsroom", SourceTier.PRIMARY, "tesla-official", Stance.SUPPORTS,
                    "Company newsroom post describes the October 15 demonstration and links the full unedited stream."),
                _ev("e2", "c1", "Reuters", SourceTier.WIRE_OR_MAJOR, "reuters-wire", Stance.SUPPORTS,
                    "Wire report from journalists present at the event describes the same demonstration."),
                _ev("e3", "c1", "AP", SourceTier.WIRE_OR_MAJOR, "reuters-wire", Stance.SUPPORTS,
                    "Second wire story; text analysis shows it is syndicated from the same wire copy as e2."),
            ],
        ),
        expected_media_verdict=MediaVerdict.AUTHENTIC,
        expected_claim_verdicts={"c1": ClaimVerdict.SUPPORTED},
    ),

    # 2 — Real footage, false caption
    EvalCase(
        id="real_footage_false_caption",
        description="Genuine 2019 protest clip reposted as if it were this week's event.",
        bundle=EvidenceBundle(
            submission_id="sub-002", submission_type=SubmissionType.VIDEO,
            caption="Huge protests in the capital TODAY — media is silent!",
            current_date="2026-10-30",
            claims=[Claim(id="c1", text="This video shows protests in the capital on October 30, 2026.",
                          normalized_text="Video shows protests in the capital on 2026-10-30.")],
            media_signals=MediaSignals(
                c2pa_status=C2PAStatus.ABSENT,
                detector_scores=[DetectorScore(name="clip-vit-ensemble", score=0.08)],
                first_seen_at="2019-06-12", original_uploader="local news channel (2019 upload)"),
            evidence=[
                _ev("e1", "c1", "Lead Stories", SourceTier.FACT_CHECK, "leadstories-check", Stance.CONTRADICTS,
                    "Fact-check traces the clip to a June 2019 protest in a different city; frame-matches the 2019 upload."),
                _ev("e2", "c1", "National Broadcaster Archive", SourceTier.WIRE_OR_MAJOR, "broadcaster-archive", Stance.CONTRADICTS,
                    "Broadcaster's own archive entry dates the footage to 2019 and names the original event."),
            ],
        ),
        expected_media_verdict=MediaVerdict.AUTHENTIC,
        expected_claim_verdicts={"c1": ClaimVerdict.FALSE},
    ),

    # 3 — Synthetic media, true claim
    EvalCase(
        id="synthetic_media_true_claim",
        description="An AI-generated illustration of a real, confirmed product launch.",
        bundle=EvidenceBundle(
            submission_id="sub-003", submission_type=SubmissionType.IMAGE,
            caption="First look at the new phone unveiled this morning!",
            current_date="2026-10-30",
            claims=[Claim(id="c1", text="The manufacturer unveiled this phone model on October 30, 2026.",
                          normalized_text="Manufacturer unveiled phone model on 2026-10-30.")],
            media_signals=MediaSignals(
                c2pa_status=C2PAStatus.ABSENT,
                detector_scores=[DetectorScore(name="clip-vit-ensemble", score=0.94)],
                forensic_flags=["Lighting and reflections inconsistent across the device surface"],
                watermarks=["Partial creator watermark typical of a public image generator"]),
            evidence=[
                _ev("e1", "c1", "Manufacturer Newsroom", SourceTier.PRIMARY, "maker-official", Stance.SUPPORTS,
                    "Official launch post confirms the model name, specs, and this morning's unveil date."),
                _ev("e2", "c1", "The Verge", SourceTier.WIRE_OR_MAJOR, "verge-report", Stance.SUPPORTS,
                    "Outlet's hands-on report from the launch event confirms the unveiling; notes circulating 'photos' are renders."),
            ],
        ),
        expected_media_verdict=MediaVerdict.SYNTHETIC,
        expected_claim_verdicts={"c1": ClaimVerdict.SUPPORTED},
    ),

    # 4 — AI product that does not exist
    EvalCase(
        id="ai_product_fake",
        description="Polished AI video advertises a product the company says it never made.",
        bundle=EvidenceBundle(
            submission_id="sub-004", submission_type=SubmissionType.VIDEO,
            caption="New gadget charges your car while you drive — order now!",
            current_date="2026-10-30",
            claims=[Claim(id="c1", text="The company sells a device that charges an EV while driving.",
                          normalized_text="Company sells a while-driving EV charging device.")],
            media_signals=MediaSignals(
                detector_scores=[DetectorScore(name="clip-vit-ensemble", score=0.88)],
                plausibility_flags=["Reflection shows three door handles; product has two",
                                    "Charging cable visible while car is in motion"]),
            evidence=[
                _ev("e1", "c1", "Company Support Statement", SourceTier.PRIMARY, "company-denial", Stance.CONTRADICTS,
                    "The company states it makes no such product and the video is not theirs."),
                _ev("e2", "c1", "AAP FactCheck", SourceTier.FACT_CHECK, "aap-check", Stance.CONTRADICTS,
                    "Fact-check finds no such product in the catalogue and identifies AI artifacts in the video."),
            ],
        ),
        expected_media_verdict=MediaVerdict.SYNTHETIC,
        expected_claim_verdicts={"c1": ClaimVerdict.FALSE},
    ),

    # 5 — Breaking news, thin coverage -> unverified / developing
    EvalCase(
        id="breaking_news_unverified",
        description="Claim about an event two hours old; one low-tier blog post is all that exists.",
        bundle=EvidenceBundle(
            submission_id="sub-005", submission_type=SubmissionType.TEXT,
            caption="Bridge collapse reported just now, casualties feared",
            current_date="2026-10-30",
            claims=[Claim(id="c1", text="A bridge collapsed today, October 30, 2026.",
                          normalized_text="A bridge collapsed on 2026-10-30.")],
            media_signals=MediaSignals(),
            evidence=[
                _ev("e1", "c1", "City Rumor Blog", SourceTier.OTHER, "rumor-blog", Stance.SUPPORTS,
                    "A single local blog post repeats the claim with no named source, photos, or official confirmation.",
                    date="2026-10-30"),
            ],
        ),
        expected_media_verdict=MediaVerdict.UNKNOWN,
        expected_claim_verdicts={"c1": ClaimVerdict.UNVERIFIED},
        expected_status=ReportStatus.DEVELOPING,
    ),

    # 6 — Spliced real clips -> edited media, misleading claim
    EvalCase(
        id="spliced_clips_misleading",
        description="Two real clips of a public figure joined to invent a statement never made in full.",
        bundle=EvidenceBundle(
            submission_id="sub-006", submission_type=SubmissionType.VIDEO,
            caption="Watch her admit the policy was a lie!",
            current_date="2026-10-30",
            claims=[Claim(id="c1", text="The official admitted in this speech that the policy was a lie.",
                          normalized_text="Official stated the policy was a lie in one speech.")],
            media_signals=MediaSignals(
                detector_scores=[DetectorScore(name="clip-vit-ensemble", score=0.21)],
                forensic_flags=["Audio waveform discontinuity mid-sentence",
                                "Background crowd changes between the two halves"]),
            evidence=[
                _ev("e1", "c1", "PolitiFact", SourceTier.FACT_CHECK, "politifact-check", Stance.CONTRADICTS,
                    "Fact-check locates both halves in speeches from different years; the sentence was never spoken as presented."),
                _ev("e2", "c1", "Parliamentary Record", SourceTier.PRIMARY, "official-transcripts", Stance.CONTEXT,
                    "Official transcripts of both speeches confirm the two quotes are real but from separate occasions."),
            ],
        ),
        expected_media_verdict=MediaVerdict.EDITED,
        expected_claim_verdicts={"c1": ClaimVerdict.MISLEADING},
    ),

    # 7 — Satire shared as news
    EvalCase(
        id="satire_as_news",
        description="A labelled satire article screenshotted and shared as a real announcement.",
        bundle=EvidenceBundle(
            submission_id="sub-007", submission_type=SubmissionType.LINK,
            caption="Government announces free fuel for everyone next month!!",
            current_date="2026-10-30",
            claims=[Claim(id="c1", text="The government announced free fuel for all citizens next month.",
                          normalized_text="Government announced free fuel for all citizens.")],
            media_signals=MediaSignals(),
            evidence=[
                _ev("e1", "c1", "The Satire Source (About page)", SourceTier.PRIMARY, "satire-about", Stance.CONTRADICTS,
                    "The publishing site's own About page states all stories are satire and fictional."),
                _ev("e2", "c1", "Ministry of Energy", SourceTier.PRIMARY, "ministry-statement", Stance.CONTRADICTS,
                    "The ministry's official channels carry no such announcement; a spokesperson post calls the story fabricated.",
                    date="2026-10-29"),
            ],
        ),
        expected_media_verdict=MediaVerdict.UNKNOWN,
        expected_claim_verdicts={"c1": ClaimVerdict.MISLEADING},
    ),

    # 8 — Plain supported story (control)
    EvalCase(
        id="plain_supported_story",
        description="Ordinary news event confirmed by two truly independent high-tier sources.",
        bundle=EvidenceBundle(
            submission_id="sub-008", submission_type=SubmissionType.LINK,
            caption="National bank cuts its key interest rate by 0.5 points",
            current_date="2026-10-30",
            claims=[Claim(id="c1", text="The national bank cut its key rate by 0.5 points on October 29, 2026.",
                          normalized_text="National bank cut key rate by 0.5 points on 2026-10-29.")],
            media_signals=MediaSignals(),
            evidence=[
                _ev("e1", "c1", "National Bank Press Release", SourceTier.PRIMARY, "bank-release", Stance.SUPPORTS,
                    "The bank's official release announces the 0.5-point cut and its effective date.", date="2026-10-29"),
                _ev("e2", "c1", "Reuters", SourceTier.WIRE_OR_MAJOR, "reuters-economy", Stance.SUPPORTS,
                    "Wire coverage independently reports the same decision and quotes the governor's press conference.",
                    date="2026-10-29"),
            ],
        ),
        expected_media_verdict=MediaVerdict.UNKNOWN,
        expected_claim_verdicts={"c1": ClaimVerdict.SUPPORTED},
    ),
]

CASES_BY_ID = {c.id: c for c in CASES}
