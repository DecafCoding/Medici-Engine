# Feature 1 — Core Conversation Engine

## Overview

Build the foundational conversation engine for the Medici Engine: two AI agents with assigned personas converse about a shared object, producing full transcripts logged to SQLite. This feature bootstraps the entire project from zero.

## User Story

As a creative researcher
I want to run conversations between two persona-driven AI agents given a shared object
So that I can generate raw creative collision transcripts to mine for novel ideas

## Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Total Tasks**: 28 across 6 PBIs
**Branch**: `feat/conversation-engine`

---

## PBI Breakdown

Execute in order. Each PBI is independently testable.

| PBI | Name | Tasks | Files | Dependencies |
|-----|------|-------|-------|-------------|
| [PBI 1](feature1-pbi-01-scaffold-and-config.md) | Scaffold & Configuration | 1–5 | pyproject.toml, .gitignore, .env.example, src/config.py | None |
| [PBI 2](feature1-pbi-02-database-layer.md) | Database Layer | 6–8 | src/db/schema.py, src/db/queries.py | PBI 1 |
| [PBI 3](feature1-pbi-03-persona-library.md) | Persona Library | 9–11 | src/personas/models.py, src/personas/library.py | PBI 1 |
| [PBI 4](feature1-pbi-04-conversation-engine.md) | Conversation Engine | 12–14 | src/engine/models.py, src/engine/conversation.py | PBI 1, 3 |
| [PBI 5](feature1-pbi-05-api-cli-integration.md) | API, CLI & Integration | 15–19 | src/main.py, src/api/routes.py, scripts/run_conversation.py | PBI 1–4 |
| [PBI 6](feature1-pbi-06-tests-and-validation.md) | Tests & Validation | 20–28 | tests/ (8 files) | PBI 1–5 |

**Note**: PBI 2 and PBI 3 are independent of each other and can be implemented in parallel.

---

## Architecture

```
API Layer          (src/api/)         ← PBI 5
       ↓
Engine Layer       (src/engine/)      ← PBI 4
       ↓
Persona Library    (src/personas/)    ← PBI 3
       ↓
Data Layer         (src/db/)          ← PBI 2
       ↓
Configuration      (src/config.py)    ← PBI 1
```

---

## Done When

- Two agents complete a full conversation from a shared object
- The transcript is logged to SQLite
- The conversation shows genuine persona-driven divergence
- All tests pass with mocked LLM calls
- Ruff lint and format pass with zero errors
- CLI and API are functional

---

## Key Risks

1. **Chat template mismatch** with MythoMax-L2-13B on vLLM
2. **Context window overflow** at 10 turns (~6K tokens vs 4K default)
3. **Persona bleed** — model may not maintain voice across all turns

**Confidence Score**: 8/10
