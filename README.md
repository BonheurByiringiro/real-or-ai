# Real or AI — Media and Claim Verification Platform

> **For the GitHub "About" field** (owner pastes this — it can't be set
> through the API connection):
> *Evidence-backed media & claim verification: two independent verdicts
> per submission (is the media real? is the story true?) from a Muse
> reasoning agent with citation guardrails enforced in code, plus an
> evaluation harness. Python · Meta Model API · Pydantic · pytest*

**Two verdicts, never one.** Every submission is judged twice:
is the *media* real (authentic / synthetic / edited / unknown), and is
the *claim* attached to it true (supported / false / misleading /
unverified)? Both verdicts must cite retrieved evidence — a detector
score alone never decides anything.

This repo implements **Phase 0** of the design document: the reasoning
agent, its schemas, its guardrails, and the evaluation harness that
tells us whether the agent is actually any good.

## Quick start (offline — no API key, no cost)

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows (Bwayne's machine)
# source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

python -m pytest tests/ -q        # 13 offline tests, incl. a fake Muse API client
python eval_harness.py            # validates the 8 hand-built eval cases
```

## Live run (calls Muse, via the Meta Model API)

The reasoning model is **Muse** — Meta's Muse family. (The original
design doc named a different vendor's model because the idea was
drafted there; the project has been Muse's since Phase 0.)

1. Go to [dev.meta.ai](https://dev.meta.ai), sign in, add billing,
   and create an API key.
2. Set it as an environment variable — never in a file:

```powershell
$env:MODEL_API_KEY = "..."        # Windows User env var works too
python eval_harness.py --live
```

Optional: `$env:REAL_OR_AI_MODEL` picks the model
(default `muse-spark-1.3`; `muse-wonder-1.0` is the most capable
tier for harder cases). The runner asks the model for a strict
`submit_report` function call — and validates the returned report
in Python either way, because the call mechanism is never the
guarantee; the validation is.

## Files

| File | What it is |
|---|---|
| `verifier_agent.py` | Schemas (`EvidenceBundle`, `Report`), system prompt, `VerifierAgent` runner, and `validate_report()` — the guardrails enforced in code |
| `cases.py` | 8 hand-built evidence bundles with expected verdicts (hard patterns: real-but-strange, real footage/false caption, synthetic media/true claim…) |
| `eval_harness.py` | `--validate` (offline case checks) and `--live` (scores the real agent, failures categorized) |
| `tests/` | Offline pytest suite |
| `PLAN.md` | Phase plan, what's parked, and working rules |

## The guardrails (the interesting part)

The prompt *asks* the model to behave. `validate_report()` *checks*:

- every cited evidence ID exists in the bundle and belongs to that claim
- a non-"unverified" verdict must cite evidence of the right stance
- confidence > 0.9 requires ≥ 2 **independent** high-tier sources
  (syndicated copies count once) or valid C2PA provenance
- the two verdicts are judged independently

## Roadmap

Phase 0 (this) → Phase 1: link ingestion + claim extraction + live
evidence retrieval → Phase 2: image provenance, CLIP embeddings,
origin tracing. Video, documents, and bots are parked — see PLAN.md.
