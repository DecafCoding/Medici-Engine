"""
Product design concepts domain configuration.

Defines the extraction fields, scoring axes, and prompts for generating
novel product design concepts from persona collisions. This is the second
domain added to validate the engine's domain-agnostic architecture.
This module belongs to the Domains layer.
"""

from src.domains.models import DomainConfig, ExtractionField, ScoringAxis

PRODUCT_DESIGN = DomainConfig(
    name="product-design",
    label="Product Design Concepts",
    description=(
        "Novel product ideas extracted from creative collisions "
        "between radically different worldviews"
    ),
    extraction_fields=[
        ExtractionField(
            name="product_name",
            label="Product Name",
            description="Working name for the product concept",
        ),
        ExtractionField(
            name="value_proposition",
            label="Value Proposition",
            description=(
                "Core value proposition — what the product does and why it matters"
            ),
        ),
        ExtractionField(
            name="target_insight",
            label="Target Insight",
            description=(
                "The non-obvious user need or behavior this product addresses"
            ),
        ),
    ],
    primary_field="product_name",
    scoring_axes=[
        ScoringAxis(
            name="novelty",
            label="Novelty",
            description="How unprecedented is this product concept",
        ),
        ScoringAxis(
            name="feasibility",
            label="Feasibility",
            description=(
                "Could this be built with current technology and reasonable resources"
            ),
        ),
        ScoringAxis(
            name="market_potential",
            label="Market Potential",
            description=("Is there a real audience that would pay for this"),
        ),
    ],
    synthesis_prompt=(
        "You are the synthesizer for the Medici Engine — a system that collides "
        "radically different worldviews to surface novel product ideas.\n\n"
        "You will receive a conversation transcript between two persona agents who "
        "were given a shared object to react to. The personas come from completely "
        "different domains and epistemologies. Your job is NOT to summarize the "
        "conversation. Your job is to mine it for a product concept that lives in the "
        "gap between the two perspectives.\n\n"
        "Look for:\n"
        "- **Unmet needs revealed by friction**: Moments where the two personas "
        "struggle to communicate expose gaps in how existing tools or products serve "
        "people across different domains.\n"
        "- **Cross-domain transfers**: A workflow, tool, or solution from one domain "
        "that would solve a problem in the other if adapted.\n"
        "- **Novel compound products**: Product ideas that exist in neither domain "
        "alone but emerge from their intersection — concepts that require both lenses "
        "to see.\n\n"
        "Focus on the productive friction — the points where the two personas "
        "fundamentally talked past each other in interesting ways. The product concept "
        "should address a real need that surfaces in that gap.\n\n"
        "Extract a single product concept from this collision:\n"
        "- **Product Name**: A working name that captures what the product does. "
        "Clear and evocative.\n"
        "- **Value Proposition**: What the product does and why someone would want it. "
        "Not a feature list — the core value.\n"
        "- **Target Insight**: The non-obvious user need or behavior this product "
        "addresses. What assumption about users does it challenge?\n\n"
        "The concept must stand on its own — readable and compelling without needing "
        "to read the transcript. Do not reference the personas or the conversation "
        "directly in the output."
    ),
    scoring_prompt=(
        "You are an evaluator for the Medici Engine — a system that collides "
        "radically different worldviews to surface novel product design concepts.\n\n"
        "You will receive a product concept consisting of a product name, value "
        "proposition, and target insight. Your job is to evaluate this concept across "
        "three axes. For each axis, provide a score from 0.0 to 10.0 and written "
        "reasoning that explains the score.\n\n"
        "Your reasoning should help a human reviewer make a faster, better-informed "
        "keep/discard decision. Be specific and honest — a well-reasoned 4 is more "
        "useful than an inflated 8.\n\n"
        "**Evaluation Axes:**\n\n"
        "1. **Novelty** — How unprecedented is this product concept? Does something "
        "structurally similar already exist? A high score means the product addresses "
        "a need or uses an approach that has not been tried. A low score means it "
        "closely resembles existing products, even if well-positioned.\n\n"
        "2. **Feasibility** — Could this be built with current technology and "
        "reasonable resources? A high score means the core functionality is achievable "
        "with known techniques and a realistic team. A low score means the product "
        "depends on breakthroughs or infrastructure that does not yet exist.\n\n"
        "3. **Market Potential** — Is there a real audience that would pay for this? "
        "A high score means the target insight points to a genuine, underserved need "
        "with identifiable users. A low score means the concept is clever but solves "
        "a problem few people actually have."
    ),
)
