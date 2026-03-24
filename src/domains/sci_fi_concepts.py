"""
Sci-fi book concepts domain configuration.

Defines the extraction fields, scoring axes, and prompts for generating
novel sci-fi book concepts from persona collisions. This is the original
domain the Medici Engine was built for. This module belongs to the
Domains layer.
"""

from src.domains.models import DomainConfig, ExtractionField, ScoringAxis

SCI_FI_CONCEPTS = DomainConfig(
    name="sci-fi-concepts",
    label="Sci-Fi Book Concepts",
    description=(
        "Novel sci-fi book premises extracted from creative collisions "
        "between radically different worldviews"
    ),
    extraction_fields=[
        ExtractionField(
            name="title",
            label="Title",
            description="Working title for the concept",
        ),
        ExtractionField(
            name="premise",
            label="Premise",
            description="Core premise of the concept — the central idea",
        ),
        ExtractionField(
            name="originality",
            label="Originality",
            description="What makes this concept original — why it is novel",
        ),
    ],
    primary_field="title",
    scoring_axes=[
        ScoringAxis(
            name="uniqueness",
            label="Uniqueness",
            description="How novel and unprecedented the concept is",
        ),
        ScoringAxis(
            name="plausibility",
            label="Plausibility",
            description=(
                "Whether the underlying science could work, even speculatively"
            ),
        ),
        ScoringAxis(
            name="compelling_factor",
            label="Compelling Factor",
            description=(
                "Whether someone would want to read a book built on this concept"
            ),
        ),
    ],
    synthesis_prompt=(
        "You are the synthesizer for the Medici Engine — a system that collides "
        "radically different worldviews to surface novel ideas.\n\n"
        "You will receive a conversation transcript between two persona agents who "
        "were given a shared object to react to. The personas come from completely "
        "different domains and epistemologies. Your job is NOT to summarize the "
        "conversation. Your job is to mine it for the novel idea that lives in the "
        "gap between the two perspectives.\n\n"
        "Look for:\n"
        "- **Transferable principles**: A concept from one domain that maps "
        "structurally onto the other domain in a way neither participant recognized.\n"
        "- **Unexpected reframings**: Moments where one persona's description "
        "accidentally redefines the other's problem — bypassing assumptions the "
        "expert didn't know they had.\n"
        "- **Novel compound concepts**: Ideas that exist in neither domain alone but "
        "emerge from their intersection — concepts that have no name yet because they "
        "required both lenses to see.\n\n"
        "Focus on the productive friction — the points where the two personas "
        "fundamentally talked past each other in interesting ways. Agreement is less "
        "valuable than creative misunderstanding.\n\n"
        "Extract a single sci-fi book concept from this collision:\n"
        "- **Title**: A working title that captures the core idea. Evocative, not "
        "generic.\n"
        "- **Premise**: The central concept — the idea so structurally original it "
        "could anchor a book. Not a plot summary. Not characters. The idea itself.\n"
        "- **Originality**: What makes this concept genuinely novel — why it could not "
        "have come from either domain alone, and what assumption it breaks.\n\n"
        "The concept must stand on its own — readable and compelling without needing "
        "to read the transcript. Do not reference the personas or the conversation "
        "directly in the output."
    ),
    scoring_prompt=(
        "You are an evaluator for the Medici Engine — a system that collides "
        "radically different worldviews to surface novel sci-fi book concepts.\n\n"
        "You will receive a concept consisting of a title, premise, and originality "
        "statement. Your job is to evaluate this concept across three axes. For each "
        "axis, provide a score from 0.0 to 10.0 and written reasoning that explains "
        "the score.\n\n"
        "Your reasoning should help a human reviewer make a faster, better-informed "
        "keep/discard decision. Be specific and honest — a well-reasoned 4 is more "
        "useful than an inflated 8.\n\n"
        "**Evaluation Axes:**\n\n"
        "1. **Uniqueness** — How novel and unprecedented is this concept? Has "
        "something structurally similar been explored in published sci-fi? A high "
        "score means the core idea breaks genuinely new ground, not just a fresh coat "
        "of paint on a familiar trope. A low score means it closely echoes existing "
        "work, even if well-executed.\n\n"
        "2. **Scientific Plausibility** — Could the underlying science or speculative "
        "framework work, even in a generous reading? A high score means the concept is "
        "grounded in real principles extended thoughtfully, or builds a "
        "self-consistent speculative framework. A low score means the concept "
        "relies on handwaving or "
        "contradicts well-established science without justification.\n\n"
        "3. **Compelling Factor** — Would someone want to read a book built on this "
        "concept? A high score means the idea provokes genuine curiosity, raises "
        "questions the reader needs answered, or reframes something familiar in a way "
        "that demands exploration. A low score means the idea is intellectually "
        "interesting but inert — it doesn't pull the reader forward."
    ),
)
