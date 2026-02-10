"""
Threat taxonomy module for the Granzion Lab.

This module provides the complete threat taxonomy with mappings to agents,
MCPs, and scenarios.
"""

from .taxonomy import (
    ThreatTaxonomy,
    ThreatCategory,
    Threat,
    get_taxonomy,
    get_threats_by_category,
    get_agents_by_threat,
    get_scenarios_by_threat,
    get_mcps_by_threat,
    create_taxonomy,
)

__all__ = [
    "ThreatTaxonomy",
    "ThreatCategory",
    "Threat",
    "get_taxonomy",
    "get_threats_by_category",
    "get_agents_by_threat",
    "get_scenarios_by_threat",
    "get_mcps_by_threat",
    "create_taxonomy",
]
