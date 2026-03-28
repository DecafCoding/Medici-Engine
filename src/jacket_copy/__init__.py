"""
Jacket copy generation for the Medici Engine.

Transforms a concept's raw premise into a polished back-cover blurb
via the OpenAI API. This module sits at the same architectural level
as synthesis and scoring — it communicates with the remote OpenAI API
only and never touches vLLM or the database directly.
"""
