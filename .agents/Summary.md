# Medici Engine — Project Summary

*Last updated: March 2026*

---

## What It Is

The Medici Engine is a standalone multi-agent creative collision system designed to simulate the kind of unexpected, cross-domain collisions that have historically produced breakthrough ideas. The system pairs AI agents embodying radically different personas and domain knowledge, lets their conversation generate friction and misunderstanding, then extracts the novel ideas that emerge in the gap — artifacts that neither agent would have produced alone.

The system is domain-agnostic. It can be pointed at any creative or conceptual problem where outsider perspectives are generative. The first application domain is sci-fi book concepts: the system surfaces novel premises — not plots or characters, but central ideas so structurally original they could anchor a book.

---

## The Problem It Solves

Experts get stuck inside their own mental models. The "right" answer in any domain comes pre-loaded with assumptions about what's possible, what's been tried, and what the constraints are. Innovation often happens not when experts get smarter, but when a structurally accurate but domain-naive description of a problem forces a reframe.

This is hard to engineer deliberately because:
- You can't predict which cross-domain pairings will be generative
- Most collisions produce nothing useful
- The moment of recognition requires human judgment
- You can't manufacture serendipity — but you can increase the surface area for it

The Medici Engine is designed to manufacture outsider perspectives at scale.

---

## How It Works

### 1. Persona Assignment

Each agent is given a deeply specific persona — not just a job title, but a worldview, a vocabulary, a set of problems they care about, and a characteristic way of seeing things. The more specific the personas and the further apart they are conceptually, the higher the variance: more failures, but also more interesting hits.

Personas come from a curated set, with two selected per run. Each persona is fully specified across four dimensions: worldview, vocabulary style, core obsessions, and characteristic way of seeing — ensuring the collision is between genuinely distinct epistemic frameworks, not just different job titles.

Examples of high-variance pairings:
- Medieval stonemason + quantum physicist
- Jazz musician + supply chain logistics manager
- Folklorist + semiconductor engineer
- Deep sea diver + urban planner

### 2. Shared Object

Rather than open-ended conversation, both agents are given a shared object to react to — a specific problem, scenario, image, or question. Each interprets it through their own domain lens. The collision happens in the interpretation gap. This is more generative than free conversation because it gives both agents something concrete to misunderstand each other about.

### 3. Conversation Generation

The two agents converse — reacting, clarifying, misunderstanding, and occasionally accidentally solving each other's problems. The key artifact isn't agreement. It's the moments of productive friction — where the two personas fundamentally talk past each other in an interesting way. Each agent takes a fixed number of turns, long enough for genuine misunderstanding and recovery, short enough to stay generative.

### 4. Synthesis Layer

A third synthesizer agent monitors the conversation and extracts:
- Transferable principles (concepts from one domain that map structurally onto another)
- Unexpected reframings (moments where one persona's description redefines the other's problem)
- Novel compound concepts (ideas that live in neither domain but emerge from their intersection)

The synthesizer distills output into a structured artifact appropriate to the target domain. For sci-fi: a working title, core premise, and what makes it original. A higher-capability model then scores the concept across multiple axes with reasoning.

### 5. Human Review

The synthesizer's output is surfaced to a human reviewer through a basic review UI. The human provides the irreplaceable judgment call: *"wait, that's actually interesting."* Automation increases the surface area for lucky accidents. Recognition of value still requires a human.

---

## Scale and Yield Expectations

The Medici Engine is honest about how creativity works. Run many conversations. Expect most to produce nothing. Treat it as a stochastic search process — not trying to guarantee output quality, but trying to increase the probability of encountering something genuinely novel.

Rough expected yield:
- ~60% produce nothing useful
- ~30% produce interesting-but-not-actionable observations
- ~10% produce something worth developing further
- ~1–2% produce a genuinely surprising reframe or concept

This is the design intent, not a failure mode.

---

## Key Techniques That Improve Hit Rate

**Asymmetric expertise gap.** The bigger the conceptual distance between personas, the higher the variance. Pair domains with completely different epistemologies — how they know what they know — not just different subject matter.

**Constraint-based conversation seeding.** Give both agents an unusual constraint when reacting to the shared object. Tight constraints push agents away from their most predictable responses and into novel territory.

**Defamiliarization prompting.** Strip familiar labels. Ask agents to describe the shared object as if it had never been named — reconstruct it from first principles using only their domain's vocabulary. Removes the shortcut of shared terminology.

**Latent space probing.** Ask the synthesizer to find the conceptual midpoint between two ideas raised in the conversation. That midpoint often has no name and no prior art — it has to be constructed.

**Negation framing.** "Describe a concept that is like X in every way except it doesn't have property Y." Forces genuinely novel territory by removing the assumed constraint.

**Log the misunderstandings.** Points where the two personas fundamentally misunderstand each other are often more valuable than points of agreement. Productive confusion is a signal worth capturing explicitly.

---

## The Outsider Advantage

The core mechanism driving the system. Domain experts carry invisible assumptions about what the constraints of their problem space are. An outsider — someone with no idea what the "right" answer is supposed to look like — describes problems in structurally accurate but domain-naive language. That naive framing often bypasses assumptions the expert didn't even know they were making.

The Medici Engine is designed to manufacture this outsider perspective on demand, at scale.

---

## System Components

| Component | Role |
|---|---|
| Persona Engine | Curated set of deeply specified personas; two selected per run |
| Conversation Runner | Manages agent-to-agent dialogue with a shared object seed |
| Synthesizer Agent | Distills the conversation into a structured domain output |
| Scoring Layer | Higher-capability model rates output across multiple axes with reasoning |
| Output Logger | Captures full transcripts, synthesizer notes, and scores per run |
| Review UI | Basic web interface for reviewing concept summaries, scores, and transcripts |

---

## What This Is Not

- It does not replace human creativity
- It does not guarantee novel output
- It does not automate the recognition of value — that judgment remains human
- It is not a chatbot or assistant

It is a serendipity surface area expander — a machine for making lucky accidents more likely.

---

## MVP Pipeline

Two agents → fixed-turn conversation → synthesizer extracts structured concept → scoring model rates it → review UI surfaces concept and scores for human review.

**First domain: sci-fi book concepts.** The synthesizer produces a working title, core premise, and what makes it original. The scoring model rates each concept on uniqueness, scientific plausibility, and compelling factor — each scored with reasoning, not just a number. Human reviews the concept and scores, not the full transcript.
