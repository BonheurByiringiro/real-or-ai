# Real or AI — Build Plan

Owner: Bwayne · Started: 2026-11-06 · Source: Project Design Document v1 (Oct 30, 2026)

Purpose (Bwayne's words): a project to help him as an AI engineer stay
up-to-date with current technologies and learn something new.
So: Python throughout (code he can follow), each phase teaches one new
skill cluster, nothing is a black box.

## The idea in one paragraph
Every submission gets TWO independent verdicts — media (authentic /
synthetic / edited / unknown) and claim (supported / false / misleading /
unverified) — and both must be backed by retrieved evidence cited by ID.
A detector score is one weak signal, never the verdict.

## Phase 0 — Foundations (IN PROGRESS)
Teaches: Pydantic schemas for LLM I/O, structured/tool-call outputs,
prompt guardrails enforced in code, evaluation harnesses.

- [x] `verifier_agent.py` — EvidenceBundle / Report schemas (doc §8.12, §9),
      system prompt (doc §8.12 rules 1–7), runner, programmatic guardrails:
      * non-"unverified" claim verdicts must cite evidence
      * cited evidence IDs must exist in the bundle and belong to that claim
      * confidence > 0.9 needs ≥2 independent high-tier sources or
        definitive provenance (valid C2PA)
      * syndicated copies in one independence group count once
- [x] `cases.py` — 8 hand-built evidence bundles covering the hard patterns:
      real-but-strange event, real footage + false caption, synthetic media +
      true claim, AI product that doesn't exist, breaking news (unverified),
      spliced clip (misleading), satire-as-news, plain supported story.
      (Doc asks for 20–30; we grow the set as we find real fact-checks.)
- [x] `eval_harness.py` — `validate` mode (offline, no API key: are the
      bundles sound and are the expected verdicts reachable under the
      guardrails?) and `live` mode (calls Muse, scores verdicts,
      categorizes failures).
- [x] Offline pytest suite incl. a fake Muse API client — tests the
      runner and guardrails with no API key and no cost.
- [ ] Live run once Bwayne creates a Meta Model API key (MODEL_API_KEY
      from dev.meta.ai; billing first). Exit criteria from the doc:
      agent matches expected verdicts on most cases; failures categorized.

### Model decision (Bwayne, 2026-11-06)
"Everything to be yours" — the reasoning model is Muse (Meta), not
Anthropic Claude (the doc named Claude only because Bwayne drafted the
idea in that tool). Access route, verified 2026-11-06 at dev.meta.ai:
Meta Model API, base URL https://api.meta.ai/v1, OpenAI-SDK compatible
(Responses API + function tools), auth MODEL_API_KEY. Default model
muse-spark-1.3 (REAL_OR_AI_MODEL); muse-wonder-1.0 is the step-up.
The runner asks for the submit_report function call, falls back to
tool_choice "required" if a forced named call is rejected, and —
regardless of mechanism — validates the returned report in Python.
The lesson: never trust the call mechanism, always validate output.

## Phase 1 — Claim + link verification (next)
Teaches: web retrieval / agentic search, source tiering, SSRF safety.
Link ingestion (safe fetching), LLM claim extraction, evidence retrieval
(Tavily/Exa + Google Fact Check Tools API), independence clustering,
simple report page. Orchestration: plain functions first, Celery + Redis
when it earns it; Temporal later.

## Phase 2 — Images + origin tracing
Teaches: embeddings + vector search, media provenance.
C2PA/EXIF checks, perceptual hashing, CLIP embeddings in Postgres +
pgvector, reverse image search (SerpAPI), one vendor detector baseline
(Hive or Sightengine) vs an own CLIP/ViT detector.

## Parked (each is its own project)
Video/audio deepfakes · document forensics · WhatsApp/Telegram bot ·
browser extension · GPU serving · multilingual reports (Kinyarwanda /
French / Swahili are in the doc's vision).

## Working rules
- Ask Bwayne before any commit/push (his standing rule). No repo yet —
  he creates/owns it when he's ready, same as TONA.
- Keys live in environment variables only (.env.example lists them;
  no real values in files or memory).
