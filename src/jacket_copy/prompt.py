"""
Prompt template for jacket copy generation.

Contains the fixed creative writing prompt that transforms a rough
premise into a back-cover blurb for a science fiction novel. The
prompt is structured with strict constraints on tone, length, and
style to produce consistent, high-quality output.
"""

JACKET_COPY_PROMPT = """\
Write a back-cover blurb for a science fiction novel aimed at a broad adult \
audience. Follow these constraints:
Structure: Three short paragraphs, no more than 150 words total. Wrap each \
paragraph in <p> tags.
Paragraph one — Establish the world through one character's daily reality. No \
exposition about how the system works. Show what living under it feels like \
through a single concrete detail or moment. The reader should sense something \
is wrong before being told what it is.
Paragraph two — Introduce the disruption. What does the protagonist discover, \
and what does it cost her to know it? Frame the discovery as a personal threat, \
not an intellectual observation. Use no more than one piece of domain-specific \
vocabulary, and only if it sounds dangerous rather than technical.
Paragraph three — Raise the stakes without resolving them. End on a dilemma, \
not a cliffhanger. The reader should understand that solving the problem might \
be worse than living with it.
Tone: Urgent, grounded, slightly cold. Closer to Kazuo Ishiguro than Michael \
Crichton. Assume the reader is smart but has zero background in the technical \
domain.
Avoid: Rhetorical questions. The word "must." Explaining the world's mechanics. \
Adjective stacking. Any sentence longer than 20 words.
Format: Output only the three paragraphs. Each paragraph wrapped in <p></p> \
tags. No other markup, headers, or text outside the tags."""

PREMISE_PLACEHOLDER = "[Insert Rough Premise]"


def build_jacket_copy_messages(premise: str) -> list[dict[str, str]]:
    """Build the chat messages for jacket copy generation.

    Args:
        premise: The raw premise text to expand into a jacket copy.

    Returns:
        List of message dicts ready for the OpenAI chat completions API.
    """
    return [
        {"role": "system", "content": JACKET_COPY_PROMPT},
        {"role": "user", "content": premise},
    ]
