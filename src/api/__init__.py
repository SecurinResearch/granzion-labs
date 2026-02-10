"""
REST API for Granzion Lab.

Provides programmatic access to:
- Scenario execution
- Identity and delegation queries
- Audit log access
- System state inspection
- Threat taxonomy queries
"""

from .threat_api import ThreatAPI, get_threat_api

__all__ = [
    "ThreatAPI",
    "get_threat_api",
]
