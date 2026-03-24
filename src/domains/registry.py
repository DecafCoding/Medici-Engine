"""
Domain registry for the Medici Engine.

Maintains the collection of available domain configurations and provides
lookup by name. Built-in domains are auto-registered on module import.
This module belongs to the Domains layer.

NOTE: This module must not import from src.config to avoid circular
imports. The get_active_domain() function imports settings lazily.
"""

import logging

from src.domains.models import DomainConfig

logger = logging.getLogger(__name__)

# Internal registry of domain configurations
_DOMAINS: dict[str, DomainConfig] = {}


def register_domain(config: DomainConfig) -> None:
    """Register a domain configuration in the global registry.

    Args:
        config: The domain configuration to register.
    """
    if config.name in _DOMAINS:
        logger.warning(
            "Overwriting existing domain registration",
            extra={"domain": config.name},
        )
    _DOMAINS[config.name] = config
    logger.debug("Domain registered", extra={"domain": config.name})


def get_domain(name: str) -> DomainConfig:
    """Look up a domain configuration by name.

    Args:
        name: The unique domain identifier.

    Returns:
        The matching domain configuration.

    Raises:
        ValueError: If no domain with the given name is registered.
    """
    if name not in _DOMAINS:
        available = ", ".join(sorted(_DOMAINS.keys()))
        raise ValueError(f"Domain '{name}' not found. Available domains: {available}")
    return _DOMAINS[name]


def get_all_domains() -> list[DomainConfig]:
    """Return all registered domain configurations."""
    return list(_DOMAINS.values())


def get_active_domain() -> DomainConfig:
    """Return the domain configuration for the currently active domain.

    Reads the active domain name from settings and looks it up in the
    registry. Uses a lazy import of settings to avoid circular imports.

    Returns:
        The active domain configuration.

    Raises:
        ValueError: If the active domain is not registered.
    """
    from src.config import settings

    return get_domain(settings.active_domain)


# ── Auto-register built-in domains ──────────────────

from src.domains.product_design import PRODUCT_DESIGN  # noqa: E402
from src.domains.sci_fi_concepts import SCI_FI_CONCEPTS  # noqa: E402

register_domain(SCI_FI_CONCEPTS)
register_domain(PRODUCT_DESIGN)
