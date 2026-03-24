"""
Batch orchestration for the Medici Engine.

Manages execution of multiple conversation runs as a batch,
coordinating the full pipeline: conversation -> synthesis -> scoring.
This module belongs to the API layer and orchestrates across
Engine, Synthesis, and Scoring layers.
"""
