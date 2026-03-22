"""
Scoring layer for the Medici Engine.

Evaluates concepts extracted by the synthesizer across domain-specific
axes using a higher-capability model (OpenAI o3). Each concept receives
scores and written reasoning for uniqueness, scientific plausibility,
and compelling factor. This module belongs to the Scoring layer and
communicates with the OpenAI API only — no vLLM calls.
"""
