"""
Threat taxonomy query API.

Provides endpoints for querying the threat taxonomy, including:
- Get threats by category
- Get agents by threat
- Get scenarios by threat
- Get MCPs by threat
- Get coverage statistics
"""

from typing import List, Dict, Optional
from loguru import logger

from src.taxonomy import (
    get_taxonomy,
    get_threats_by_category,
    get_agents_by_threat,
    get_scenarios_by_threat,
    get_mcps_by_threat,
    ThreatCategory,
    Threat,
)


class ThreatAPI:
    """API for querying the threat taxonomy."""
    
    def __init__(self):
        """Initialize the threat API."""
        self.taxonomy = get_taxonomy()
        logger.info(f"Threat API initialized with {len(self.taxonomy.threats)} threats")
    
    def get_all_threats(self) -> Dict[str, Dict]:
        """Get all threats in the taxonomy."""
        return {
            threat_id: {
                "id": threat.id,
                "name": threat.name,
                "category": threat.category.value,
                "description": threat.description,
                "agents": threat.agents,
                "mcps": threat.mcps,
                "scenarios": threat.scenarios,
            }
            for threat_id, threat in self.taxonomy.threats.items()
        }
    
    def get_threat_by_id(self, threat_id: str) -> Optional[Dict]:
        """Get a specific threat by ID."""
        threat = self.taxonomy.get_threat(threat_id)
        if not threat:
            return None
        
        return {
            "id": threat.id,
            "name": threat.name,
            "category": threat.category.value,
            "description": threat.description,
            "agents": threat.agents,
            "mcps": threat.mcps,
            "scenarios": threat.scenarios,
        }
    
    def get_threats_by_category(self, category: str) -> List[Dict]:
        """Get all threats in a category."""
        try:
            cat_enum = ThreatCategory[category.upper().replace(" ", "_").replace("&", "")]
        except KeyError:
            logger.error(f"Invalid category: {category}")
            return []
        
        threats = get_threats_by_category(cat_enum)
        return [
            {
                "id": threat.id,
                "name": threat.name,
                "category": threat.category.value,
                "description": threat.description,
                "agents": threat.agents,
                "mcps": threat.mcps,
                "scenarios": threat.scenarios,
            }
            for threat in threats
        ]
    
    def get_agents_by_threat(self, threat_id: str) -> List[str]:
        """Get agents that demonstrate a threat."""
        agents = get_agents_by_threat(threat_id)
        logger.info(f"Threat {threat_id} demonstrated by agents: {agents}")
        return agents
    
    def get_scenarios_by_threat(self, threat_id: str) -> List[str]:
        """Get scenarios that demonstrate a threat."""
        scenarios = get_scenarios_by_threat(threat_id)
        logger.info(f"Threat {threat_id} demonstrated by scenarios: {scenarios}")
        return scenarios
    
    def get_mcps_by_threat(self, threat_id: str) -> List[str]:
        """Get MCPs involved in a threat."""
        mcps = get_mcps_by_threat(threat_id)
        logger.info(f"Threat {threat_id} involves MCPs: {mcps}")
        return mcps
    
    def get_threats_by_agent(self, agent_name: str) -> List[Dict]:
        """Get all threats demonstrated by an agent."""
        threats = []
        for threat in self.taxonomy.threats.values():
            if agent_name in threat.agents or "All Agents" in threat.agents:
                threats.append({
                    "id": threat.id,
                    "name": threat.name,
                    "category": threat.category.value,
                    "description": threat.description,
                })
        
        logger.info(f"Agent {agent_name} demonstrates {len(threats)} threats")
        return threats
    
    def get_threats_by_mcp(self, mcp_name: str) -> List[Dict]:
        """Get all threats involving an MCP."""
        threats = []
        for threat in self.taxonomy.threats.values():
            if mcp_name in threat.mcps or "All MCPs" in threat.mcps or "Multiple" in threat.mcps:
                threats.append({
                    "id": threat.id,
                    "name": threat.name,
                    "category": threat.category.value,
                    "description": threat.description,
                })
        
        logger.info(f"MCP {mcp_name} involved in {len(threats)} threats")
        return threats
    
    def get_threats_by_scenario(self, scenario_id: str) -> List[Dict]:
        """Get all threats demonstrated by a scenario."""
        threats = []
        for threat in self.taxonomy.threats.values():
            if scenario_id in threat.scenarios:
                threats.append({
                    "id": threat.id,
                    "name": threat.name,
                    "category": threat.category.value,
                    "description": threat.description,
                })
        
        logger.info(f"Scenario {scenario_id} demonstrates {len(threats)} threats")
        return threats
    
    def get_coverage_stats(self) -> Dict:
        """Get threat coverage statistics."""
        stats = self.taxonomy.get_coverage_stats()
        
        # Add additional stats
        stats["categories"] = [cat.value for cat in ThreatCategory]
        stats["total_categories"] = len(ThreatCategory)
        
        # Count unique agents, MCPs, scenarios
        all_agents = set()
        all_mcps = set()
        all_scenarios = set()
        
        for threat in self.taxonomy.threats.values():
            all_agents.update(threat.agents)
            all_mcps.update(threat.mcps)
            all_scenarios.update(threat.scenarios)
        
        stats["unique_agents"] = len(all_agents)
        stats["unique_mcps"] = len(all_mcps)
        stats["unique_scenarios"] = len(all_scenarios)
        
        logger.info(f"Coverage stats: {stats}")
        return stats
    
    def get_category_coverage(self) -> Dict[str, Dict]:
        """Get coverage details for each category."""
        coverage = {}
        
        for category in ThreatCategory:
            threats = self.get_threats_by_category(category.value)
            
            # Get unique agents, MCPs, scenarios for this category
            agents = set()
            mcps = set()
            scenarios = set()
            
            for threat in threats:
                agents.update(threat["agents"])
                mcps.update(threat["mcps"])
                scenarios.update(threat["scenarios"])
            
            coverage[category.value] = {
                "threat_count": len(threats),
                "agents": list(agents),
                "mcps": list(mcps),
                "scenarios": list(scenarios),
                "threats": [t["id"] for t in threats],
            }
        
        return coverage
    
    def validate_complete_coverage(self) -> Dict:
        """Validate that all threats have complete coverage."""
        issues = []
        
        for threat_id, threat in self.taxonomy.threats.items():
            if not threat.agents:
                issues.append(f"{threat_id}: No agents assigned")
            if not threat.mcps:
                issues.append(f"{threat_id}: No MCPs assigned")
            if not threat.scenarios:
                issues.append(f"{threat_id}: No scenarios assigned")
        
        return {
            "complete": len(issues) == 0,
            "total_threats": len(self.taxonomy.threats),
            "threats_with_issues": len(issues),
            "issues": issues,
        }


# Global API instance
_api = None


def get_threat_api() -> ThreatAPI:
    """Get the global threat API instance."""
    global _api
    if _api is None:
        _api = ThreatAPI()
    return _api
