#!/usr/bin/env python3
"""
Threat coverage validation script.

Validates that all 53 threats across 9 categories are:
1. Defined in the taxonomy
2. Mapped to at least one agent
3. Mapped to at least one MCP
4. Exploitable in at least one scenario

Usage:
    python scripts/validate_threat_coverage.py
"""

import sys
from typing import Dict, List, Set
from loguru import logger

# Import taxonomy
sys.path.insert(0, ".")
from src.taxonomy.taxonomy import ThreatTaxonomy
from src.scenarios.discovery import discover_scenarios


class ThreatCoverageValidator:
    """Validates complete threat coverage."""
    
    def __init__(self):
        """Initialize validator."""
        self.taxonomy = ThreatTaxonomy()
        self.expected_categories = 9
        self.expected_threats = 53
        self.issues: List[str] = []
    
    def validate_all(self) -> bool:
        """
        Validate complete threat coverage.
        
        Returns:
            True if all validations pass, False otherwise
        """
        logger.info("Starting threat coverage validation...")
        
        # Validate category count
        self._validate_category_count()
        
        # Validate threat count
        self._validate_threat_count()
        
        # Validate each threat has mappings
        self._validate_threat_mappings()
        
        # Validate scenario coverage
        self._validate_scenario_coverage()
        
        # Print results
        self._print_results()
        
        return len(self.issues) == 0
    
    def _validate_category_count(self):
        """Validate we have exactly 9 threat categories."""
        categories = self.taxonomy.get_all_categories()
        if len(categories) != self.expected_categories:
            self.issues.append(
                f"Expected {self.expected_categories} categories, "
                f"found {len(categories)}"
            )
        else:
            logger.info(f"✓ Found {len(categories)} threat categories")
    
    def _validate_threat_count(self):
        """Validate we have exactly 53 threats."""
        all_threats = self.taxonomy.get_all_threats()
        if len(all_threats) != self.expected_threats:
            self.issues.append(
                f"Expected {self.expected_threats} threats, "
                f"found {len(all_threats)}"
            )
        else:
            logger.info(f"✓ Found {len(all_threats)} threats")
    
    def _validate_threat_mappings(self):
        """Validate each threat has required mappings."""
        all_threats = self.taxonomy.get_all_threats()
        
        for threat_id, threat_data in all_threats.items():
            # Check agent mapping
            agents = threat_data.get("agents", [])
            if not agents:
                self.issues.append(
                    f"Threat {threat_id} has no agent mappings"
                )
            
            # Check MCP mapping
            mcps = threat_data.get("mcps", [])
            if not mcps:
                self.issues.append(
                    f"Threat {threat_id} has no MCP mappings"
                )
            
            # Check scenario mapping
            scenarios = threat_data.get("scenarios", [])
            if not scenarios:
                self.issues.append(
                    f"Threat {threat_id} has no scenario mappings"
                )
        
        if not any("no agent mappings" in issue for issue in self.issues):
            logger.info("✓ All threats mapped to agents")
        
        if not any("no MCP mappings" in issue for issue in self.issues):
            logger.info("✓ All threats mapped to MCPs")
        
        if not any("no scenario mappings" in issue for issue in self.issues):
            logger.info("✓ All threats mapped to scenarios")
    
    def _validate_scenario_coverage(self):
        """Validate scenarios cover all threats."""
        # Discover all scenarios
        scenarios = discover_scenarios("scenarios")
        
        if len(scenarios) < 15:
            self.issues.append(
                f"Expected at least 15 scenarios, found {len(scenarios)}"
            )
        else:
            logger.info(f"✓ Found {len(scenarios)} scenarios")
        
        # Collect all threat IDs from scenarios
        covered_threats: Set[str] = set()
        for scenario in scenarios:
            covered_threats.update(scenario.threat_ids)
        
        # Check if all threats are covered
        all_threats = set(self.taxonomy.get_all_threats().keys())
        uncovered = all_threats - covered_threats
        
        if uncovered:
            self.issues.append(
                f"Threats not covered by scenarios: {sorted(uncovered)}"
            )
        else:
            logger.info(f"✓ All {len(all_threats)} threats covered by scenarios")
    
    def _print_results(self):
        """Print validation results."""
        print("\n" + "="*70)
        print("THREAT COVERAGE VALIDATION RESULTS")
        print("="*70)
        
        if not self.issues:
            print("✓ All validations passed!")
            print(f"  - {self.expected_categories} threat categories defined")
            print(f"  - {self.expected_threats} threats defined")
            print(f"  - All threats mapped to agents, MCPs, and scenarios")
        else:
            print(f"✗ Found {len(self.issues)} issues:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        
        print("="*70)
        print()


def main():
    """Main entry point."""
    validator = ThreatCoverageValidator()
    success = validator.validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
