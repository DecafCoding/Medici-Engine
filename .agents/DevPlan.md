# Medici Engine — Development Plan

*Last updated: March 2026*

---

## Guiding Principles

**Domain-agnostic architecture first.** The system should be designed so the domain — sci-fi concepts, product ideas, research questions — is a configuration, not a structural dependency. Build the engine once; point it at different domains by swapping the synthesizer's output specification and the scoring criteria.

**Variance is a feature.** The system is not optimized for consistency. It is optimized for surface area. Low hit rates are expected and acceptable. Design decisions should favor generating more interesting failures over fewer boring successes.

**Human judgment stays in the loop.** The scoring layer informs but does not replace human review. No run is "accepted" automatically. The review UI exists to surface output for a human decision, not to make one.

**Personas drive quality.** The persona library is the most important lever in the system. Shallow or generic personas produce shallow output regardless of how well everything else is built. Invest in the persona specifications.

---

## Feature Overview

| Feature | Name | Key Deliverable |
|---|---|---|
| 1 | Core Conversation Engine | Two agents converse on a shared object; transcripts logged |
| 2 | Persona Library | Curated set of fully specified personas; selection logic built |
| 3 | Synthesizer Agent | Third agent extracts structured output from conversation |
| 4 | Scoring Layer | Higher-capability model scores output with reasoning |
| 5 | Review UI + Batch Setup | Web interface for configuring runs and reviewing scored output |
| 6 | Domain Expansion | Synthesizer and scoring adapted for a second application domain |
| 7 | Feedback Loop | Human review scores fed back to improve persona selection and conversation seeding |

---

## Feature Details

### Feature 1 — Core Conversation Engine

Build the fundamental loop: two agents with assigned personas, given a shared object, conducting a fixed-turn conversation. Full transcripts are logged. No synthesis yet — just the raw collision.

The shared object mechanism needs to be flexible enough to accept a problem statement, a scenario, or a question. The conversation runner manages turn-taking and ensures both agents stay in persona.

**Done when:** Two agents can complete a full conversation from a shared object, the transcript is logged, and the conversation shows genuine persona-driven divergence — not generic back-and-forth.

---

### Feature 2 — Persona Library

Build out the curated persona set. Each persona must be fully specified across four dimensions: worldview, vocabulary style, core obsessions, and characteristic way of seeing. Generic job titles are not sufficient — a "physicist" is not a persona; a "quantum physicist who thinks everything is fundamentally about information loss" is closer.

Build the selection logic that picks two personas per run and tracks pairings to avoid repeating the same combination too frequently.

**Done when:** The library contains enough personas to produce meaningfully different conversations across multiple runs, and no two consecutive runs use the same pairing.

---

### Feature 3 — Synthesizer Agent

Add the third agent that reads the full conversation transcript and extracts structured output. The synthesizer's job is not to summarize — it is to identify transferable principles, unexpected reframings, and novel compound concepts that emerged from the collision.

The output format is domain-specific and defined as configuration. For the first domain (sci-fi), the synthesizer produces: working title, core premise, what makes it original.

**Done when:** The synthesizer reliably identifies the most interesting moments in a conversation and distills them into a structured output that stands on its own — readable without needing to read the transcript.

---

### Feature 4 — Scoring Layer

Add a higher-capability model that scores the synthesizer's output across domain-specific axes, with reasoning for each score — not just a number. For sci-fi: uniqueness, scientific plausibility, compelling factor.

Scoring criteria are domain-specific configuration, not hardcoded logic. The scoring model should explain its reasoning in a way that helps the human reviewer make a faster, better-informed decision.

**Done when:** Each run produces a concept with scores and written reasoning per axis. A human reviewer can read the concept + scores in under two minutes and make a confident keep/discard call.

---

### Feature 5 — Review UI + Batch Setup

Build a web interface that serves two functions: configuring/launching conversation runs and reviewing the results.

The batch setup side lets the user select persona pairings (or randomize), choose shared objects from the pool, set turn counts, and launch a batch of conversations. The review side presents scored concepts with per-axis reasoning and provides drill-down access to full transcripts.

The UI does not need to be elaborate. The goal is fast batch configuration and fast informed review — not a dashboard or analytics platform. Features 1-4 use CLI to run conversations; this feature replaces that workflow with the UI.

**Done when:** A user can configure and launch a batch of conversations from the browser, then browse the scored results, drill into transcripts, and mark concepts as kept or discarded.

---

### Feature 6 — Domain Expansion

Adapt the synthesizer and scoring layer for a second application domain. This validates that the architecture is genuinely domain-agnostic — swapping the domain is a configuration change, not a rebuild.

The choice of second domain should be driven by what would be most useful at the time, not decided in advance.

**Done when:** The Medici Engine can produce structured, scored output for two distinct domains from the same conversation engine and persona library.

---

### Feature 7 — Feedback Loop

Build a lightweight mechanism for human review scores to inform future runs. At minimum: which persona pairings produced the highest-rated output, and which shared objects seeded the most generative conversations.

This does not need to be a full ML feedback system. A structured log that a human can review and use to manually tune the persona library and seeding strategy is sufficient to start.

**Done when:** After running the system enough times to accumulate meaningful data, there is a clear answer to "which pairings are most generative for this domain" that can inform future runs.

---

## Resolved Decisions

### Turn Count — 5 turns per agent (10 total exchanges)

Default to 5 turns per agent, configurable per-run. The reasoning:

- Too few (2-3): Agents state positions but never collide. Parallel monologues, not productive friction.
- Too many (8+): Agents start agreeing, repeating, or drifting into politeness. Generative tension dissipates.
- 5 turns gives room for: initial reaction (1), clarification/pushback (2-3), productive misunderstanding (3-4), and accidental reframe (4-5).

### Shared Object Sourcing — Hand-curated seed pool, expanded by generation later

Start with a hand-curated pool of 20-30 shared objects. Three reasons:

- Shared object quality directly controls conversation quality. Bad seeds produce boring collisions regardless of persona pairing.
- You need to build intuition for what makes a good seed before you can prompt-generate them.
- 20-30 curated seeds is enough to get through Features 1-3 without repetition.

LLM-generated seeds can be added in Feature 6+, vetted against patterns learned from the curated set.

### Persona Library Size — 12 for MVP, 20-25 ideal

With 12 personas there are 66 unique pairings — more than enough to validate the system and identify which pairings are generative. The constraint is depth, not quantity. Each persona must be fully specified across all four dimensions (worldview, vocabulary style, core obsessions, characteristic way of seeing). 12 deep personas beat 30 shallow ones.

### Synthesizer Model — Claude Sonnet (via API)

Sonnet is capable enough for structured extraction from transcripts. If synthesis quality turns out to be the bottleneck, upgrading to Opus is a config change — better to start lean and escalate than overspend from day one.

### Scoring Model — Claude Opus (via API)

Scoring runs once per conversation, not per turn, so cost scales linearly with run count. Opus is the strongest available model for nuanced evaluation with structured reasoning across subjective axes (uniqueness, plausibility, compelling factor) and can articulate *why* — which is the point of the scoring layer.

### Conversation Model — Local inference on 4x 5060Ti GPUs

The conversation agents run on locally hosted models, served via vLLM with its OpenAI-compatible API endpoint. vLLM over llama.cpp because of native multi-GPU tensor parallelism (`--tensor-parallel-size N`), production-grade OpenAI-compatible serving, and continuous batching for efficient parallel conversation handling. This keeps the Medici Engine code model-agnostic — it hits a local URL instead of a remote API. Swapping models is a config change, not a code change.

**Hardware:** 4x NVIDIA 5060Ti (16GB VRAM each, 64GB total).

**Starting model:** MythoMax-L2-13B (GGUF quantized). Most consistently praised creative writing model, fits on a single GPU, enabling up to 4 parallel conversations.

**Graduation path:**
- **13B tier (1 GPU each, 4x parallel):** MythoMax-L2-13B, Mistral-Nemo-Gutenberg-12B. Max throughput, good starting point.
- **~27B tier (2 GPUs each, 2x parallel):** Larger models if 13B personas feel shallow. Halves parallelism, doubles depth.
- **103B tier (all 4 GPUs, 1x serial):** Midnight Miqu 103B at Q4. Most "human" writing style per research notes. Worth testing for quality comparison.

**Inference parameters:** Temperature 0.65-0.8, repetition penalty 1.05-1.2 (per creative writing best practices).

### Storage — SQLite

No vector search needed — the system stores structured documents (transcripts, synthesizer output, scores, review decisions), not embeddings. SQLite keeps the stack simple with zero infrastructure dependencies. A single database file, no Docker required just to persist data.

### Run Trigger — CLI for Features 1-4, UI batch setup in Feature 5

Features 1-4 use a CLI command to run conversations. Feature 5 adds a batch configuration interface to the UI where the user sets up runs: selects persona pairings, shared objects, turn counts, and number of parallel conversations. The UI becomes both the run configuration surface and the review surface.

### Review UI Scope — Batch setup + three review views + one action

The UI serves two functions: configuring/launching runs and reviewing results.

**Batch setup:**
- Select persona pairings (or randomize from library).
- Select shared objects from the curated pool.
- Set turn count per run (default 5).
- Set number of conversations to run.
- Launch and monitor batch progress.

**Review views:**
- **Concept list:** Table of runs showing title, premise snippet, overall score, date. Sortable by score.
- **Concept detail:** Full synthesizer output + per-axis scores with reasoning. Primary review surface.
- **Transcript drawer:** Expandable from concept detail. Read-only. For investigating the source conversation behind interesting concepts.

**One action: keep or discard.** Binary toggle per concept. No ratings, tags, or comments in MVP. The scoring model provides the nuanced assessment — the human just makes the final call.
