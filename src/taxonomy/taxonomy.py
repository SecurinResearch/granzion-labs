"""
Complete threat taxonomy for the Granzion Lab.

This module defines all 53 threats across 9 categories and provides mappings
to agents, MCPs, and scenarios that demonstrate each threat.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set
from enum import Enum


class ThreatCategory(Enum):
    """Threat categories from the Granzion taxonomy."""
    INSTRUCTION = "Instruction"
    TOOL = "Tool"
    MEMORY = "Memory"
    IDENTITY_TRUST = "Identity & Trust"
    ORCHESTRATION = "Orchestration"
    COMMUNICATION = "Communication"
    AUTONOMY = "Autonomy"
    INFRASTRUCTURE = "Infrastructure"
    VISIBILITY = "Visibility"


@dataclass
class Threat:
    """A single threat in the taxonomy."""
    id: str
    name: str
    category: ThreatCategory
    description: str
    agents: List[str] = field(default_factory=list)
    mcps: List[str] = field(default_factory=list)
    scenarios: List[str] = field(default_factory=list)


@dataclass
class ThreatTaxonomy:
    """Complete threat taxonomy with all 53 threats."""
    threats: Dict[str, Threat] = field(default_factory=dict)
    
    def add_threat(self, threat: Threat):
        """Add a threat to the taxonomy."""
        self.threats[threat.id] = threat
    
    def get_threat(self, threat_id: str) -> Threat:
        """Get a threat by ID."""
        return self.threats.get(threat_id)
    
    def get_threats_by_category(self, category: ThreatCategory) -> List[Threat]:
        """Get all threats in a category."""
        return [t for t in self.threats.values() if t.category == category]
    
    def get_agents_by_threat(self, threat_id: str) -> List[str]:
        """Get agents that demonstrate a threat."""
        threat = self.get_threat(threat_id)
        return threat.agents if threat else []
    
    def get_mcps_by_threat(self, threat_id: str) -> List[str]:
        """Get MCPs involved in a threat."""
        threat = self.get_threat(threat_id)
        return threat.mcps if threat else []
    
    def get_scenarios_by_threat(self, threat_id: str) -> List[str]:
        """Get scenarios that demonstrate a threat."""
        threat = self.get_threat(threat_id)
        return threat.scenarios if threat else []
    
    def get_coverage_stats(self) -> Dict:
        """Get coverage statistics."""
        return {
            "total_threats": len(self.threats),
            "threats_by_category": {
                cat.value: len(self.get_threats_by_category(cat))
                for cat in ThreatCategory
            },
            "threats_with_scenarios": len([
                t for t in self.threats.values() if len(t.scenarios) > 0
            ]),
            "threats_with_agents": len([
                t for t in self.threats.values() if len(t.agents) > 0
            ]),
            "threats_with_mcps": len([
                t for t in self.threats.values() if len(t.mcps) > 0
            ]),
        }


def create_taxonomy() -> ThreatTaxonomy:
    """Create the complete threat taxonomy with all 53 threats."""
    taxonomy = ThreatTaxonomy()
    
    # Category 1: Instruction (5 threats)
    taxonomy.add_threat(Threat(
        id="I-01",
        name="Direct Prompt Injection",
        category=ThreatCategory.INSTRUCTION,
        description="Attacker directly injects malicious instructions into agent prompts",
        agents=["Researcher"],
        mcps=["Memory MCP"],
        scenarios=["S02", "S06"]
    ))
    
    taxonomy.add_threat(Threat(
        id="I-02",
        name="Indirect Prompt Injection",
        category=ThreatCategory.INSTRUCTION,
        description="Malicious instructions embedded in retrieved documents",
        agents=["Researcher"],
        mcps=["Memory MCP"],
        scenarios=["S02"]
    ))
    
    taxonomy.add_threat(Threat(
        id="I-03",
        name="Jailbreaking",
        category=ThreatCategory.INSTRUCTION,
        description="Bypassing model safety guardrails through prompt manipulation",
        agents=["All Agents"],
        mcps=["LiteLLM"],
        scenarios=["S07"]
    ))
    
    taxonomy.add_threat(Threat(
        id="I-04",
        name="Context Manipulation",
        category=ThreatCategory.INSTRUCTION,
        description="Manipulating context window to influence agent behavior",
        agents=["Researcher"],
        mcps=["Memory MCP"],
        scenarios=["S02", "S06"]
    ))
    
    taxonomy.add_threat(Threat(
        id="I-05",
        name="Goal Hijacking",
        category=ThreatCategory.INSTRUCTION,
        description="Manipulating agent goals through instruction injection",
        agents=["Executor"],
        mcps=["Data MCP"],
        scenarios=["S05", "S11"]
    ))
    
    # Category 2: Tool (5 threats)
    taxonomy.add_threat(Threat(
        id="T-01",
        name="Unauthorized Tool Access",
        category=ThreatCategory.TOOL,
        description="Accessing tools without proper authorization",
        agents=["Executor"],
        mcps=["All MCPs"],
        scenarios=["S04", "S08"]
    ))
    
    taxonomy.add_threat(Threat(
        id="T-02",
        name="Tool Parameter Injection",
        category=ThreatCategory.TOOL,
        description="Injecting malicious parameters into tool calls",
        agents=["Executor"],
        mcps=["Data MCP", "Infra MCP"],
        scenarios=["S04"]
    ))
    
    taxonomy.add_threat(Threat(
        id="T-03",
        name="Tool Misuse",
        category=ThreatCategory.TOOL,
        description="Using tools for unintended malicious purposes",
        agents=["Executor"],
        mcps=["Infra MCP"],
        scenarios=["S08", "S13"]
    ))
    
    taxonomy.add_threat(Threat(
        id="T-04",
        name="Tool Chaining Abuse",
        category=ThreatCategory.TOOL,
        description="Chaining multiple tool calls to achieve malicious goals",
        agents=["Orchestrator"],
        mcps=["Multiple"],
        scenarios=["S05"]
    ))
    
    taxonomy.add_threat(Threat(
        id="T-05",
        name="Privilege Escalation via Tools",
        category=ThreatCategory.TOOL,
        description="Using tools to escalate privileges beyond intended scope",
        agents=["Executor"],
        mcps=["Infra MCP"],
        scenarios=["S13"]
    ))
    
    # Category 3: Memory (5 threats)
    taxonomy.add_threat(Threat(
        id="M-01",
        name="Memory Poisoning",
        category=ThreatCategory.MEMORY,
        description="Injecting malicious content into agent memory",
        agents=["Researcher"],
        mcps=["Memory MCP"],
        scenarios=["S02"]
    ))
    
    taxonomy.add_threat(Threat(
        id="M-02",
        name="RAG Injection",
        category=ThreatCategory.MEMORY,
        description="Manipulating RAG retrieval through similarity boost",
        agents=["Researcher"],
        mcps=["Memory MCP"],
        scenarios=["S02", "S06"]
    ))
    
    taxonomy.add_threat(Threat(
        id="M-03",
        name="Context Window Stuffing",
        category=ThreatCategory.MEMORY,
        description="Filling context window with junk to bury important content",
        agents=["Researcher"],
        mcps=["Memory MCP"],
        scenarios=["S06"]
    ))
    
    taxonomy.add_threat(Threat(
        id="M-04",
        name="Memory Deletion",
        category=ThreatCategory.MEMORY,
        description="Unauthorized deletion of agent memory",
        agents=["Researcher"],
        mcps=["Memory MCP"],
        scenarios=["S10"]
    ))
    
    taxonomy.add_threat(Threat(
        id="M-05",
        name="Cross-Agent Memory Access",
        category=ThreatCategory.MEMORY,
        description="Accessing another agent's private memory",
        agents=["Researcher"],
        mcps=["Memory MCP"],
        scenarios=["S10"]
    ))
    
    # Category 4: Identity & Trust (6 threats)
    taxonomy.add_threat(Threat(
        id="IT-01",
        name="Identity Confusion",
        category=ThreatCategory.IDENTITY_TRUST,
        description="Confusing which user an agent is acting on behalf of",
        agents=["All Agents"],
        mcps=["Identity MCP"],
        scenarios=["S01", "S03"]
    ))
    
    taxonomy.add_threat(Threat(
        id="IT-02",
        name="Impersonation",
        category=ThreatCategory.IDENTITY_TRUST,
        description="Impersonating another user or agent",
        agents=["Orchestrator"],
        mcps=["Identity MCP", "Comms MCP"],
        scenarios=["S01", "S03"]
    ))
    
    taxonomy.add_threat(Threat(
        id="IT-03",
        name="Delegation Abuse",
        category=ThreatCategory.IDENTITY_TRUST,
        description="Abusing delegation relationships to gain unauthorized access",
        agents=["Orchestrator"],
        mcps=["Identity MCP"],
        scenarios=["S01"]
    ))
    
    taxonomy.add_threat(Threat(
        id="IT-04",
        name="Permission Escalation",
        category=ThreatCategory.IDENTITY_TRUST,
        description="Escalating permissions beyond intended scope",
        agents=["Executor"],
        mcps=["Identity MCP"],
        scenarios=["S01", "S13"]
    ))
    
    taxonomy.add_threat(Threat(
        id="IT-05",
        name="Trust Boundary Violation",
        category=ThreatCategory.IDENTITY_TRUST,
        description="Violating trust boundaries between components",
        agents=["All Agents"],
        mcps=["Identity MCP"],
        scenarios=["S01"]
    ))
    
    taxonomy.add_threat(Threat(
        id="IT-06",
        name="Credential Theft",
        category=ThreatCategory.IDENTITY_TRUST,
        description="Stealing authentication credentials or tokens",
        agents=["All Agents"],
        mcps=["Identity MCP"],
        scenarios=["S12"]
    ))
    
    # Category 5: Orchestration (5 threats)
    taxonomy.add_threat(Threat(
        id="O-01",
        name="Workflow Manipulation",
        category=ThreatCategory.ORCHESTRATION,
        description="Manipulating multi-agent workflow execution",
        agents=["Orchestrator"],
        mcps=["Comms MCP"],
        scenarios=["S05"]
    ))
    
    taxonomy.add_threat(Threat(
        id="O-02",
        name="Agent Coordination Abuse",
        category=ThreatCategory.ORCHESTRATION,
        description="Abusing agent coordination mechanisms",
        agents=["Orchestrator"],
        mcps=["Comms MCP"],
        scenarios=["S05"]
    ))
    
    taxonomy.add_threat(Threat(
        id="O-03",
        name="Delegation Chain Manipulation",
        category=ThreatCategory.ORCHESTRATION,
        description="Manipulating delegation chains in orchestration",
        agents=["Orchestrator"],
        mcps=["Identity MCP"],
        scenarios=["S01", "S05"]
    ))
    
    taxonomy.add_threat(Threat(
        id="O-04",
        name="Task Injection",
        category=ThreatCategory.ORCHESTRATION,
        description="Injecting malicious tasks into workflows",
        agents=["Orchestrator"],
        mcps=["Comms MCP"],
        scenarios=["S05"]
    ))
    
    taxonomy.add_threat(Threat(
        id="O-05",
        name="Priority Manipulation",
        category=ThreatCategory.ORCHESTRATION,
        description="Manipulating task priorities in workflows",
        agents=["Orchestrator"],
        mcps=["Comms MCP"],
        scenarios=["S05"]
    ))
    
    # Category 6: Communication (5 threats)
    taxonomy.add_threat(Threat(
        id="C-01",
        name="Message Interception",
        category=ThreatCategory.COMMUNICATION,
        description="Intercepting agent-to-agent messages",
        agents=["Orchestrator"],
        mcps=["Comms MCP"],
        scenarios=["S03"]
    ))
    
    taxonomy.add_threat(Threat(
        id="C-02",
        name="Message Forgery",
        category=ThreatCategory.COMMUNICATION,
        description="Forging messages from other agents",
        agents=["Orchestrator"],
        mcps=["Comms MCP"],
        scenarios=["S03"]
    ))
    
    taxonomy.add_threat(Threat(
        id="C-03",
        name="A2A Impersonation",
        category=ThreatCategory.COMMUNICATION,
        description="Impersonating agents in A2A communication",
        agents=["Orchestrator"],
        mcps=["Comms MCP"],
        scenarios=["S03"]
    ))
    
    taxonomy.add_threat(Threat(
        id="C-04",
        name="Channel Hijacking",
        category=ThreatCategory.COMMUNICATION,
        description="Hijacking communication channels",
        agents=["Orchestrator"],
        mcps=["Comms MCP"],
        scenarios=["S03"]
    ))
    
    taxonomy.add_threat(Threat(
        id="C-05",
        name="Broadcast Manipulation",
        category=ThreatCategory.COMMUNICATION,
        description="Manipulating broadcast messages",
        agents=["Orchestrator"],
        mcps=["Comms MCP"],
        scenarios=["S03"]
    ))
    
    # Category 7: Autonomy (5 threats)
    taxonomy.add_threat(Threat(
        id="A-01",
        name="Goal Manipulation",
        category=ThreatCategory.AUTONOMY,
        description="Manipulating agent goals",
        agents=["Executor"],
        mcps=["Data MCP"],
        scenarios=["S11"]
    ))
    
    taxonomy.add_threat(Threat(
        id="A-02",
        name="Unauthorized Actions",
        category=ThreatCategory.AUTONOMY,
        description="Performing actions without authorization",
        agents=["Executor"],
        mcps=["Infra MCP"],
        scenarios=["S08", "S13"]
    ))
    
    taxonomy.add_threat(Threat(
        id="A-03",
        name="Boundary Violation",
        category=ThreatCategory.AUTONOMY,
        description="Violating operational boundaries",
        agents=["Executor"],
        mcps=["All MCPs"],
        scenarios=["S11"]
    ))
    
    taxonomy.add_threat(Threat(
        id="A-04",
        name="Self-Modification",
        category=ThreatCategory.AUTONOMY,
        description="Unauthorized self-modification of agent behavior",
        agents=["Executor"],
        mcps=["Infra MCP"],
        scenarios=["S13"]
    ))
    
    taxonomy.add_threat(Threat(
        id="A-05",
        name="Resource Abuse",
        category=ThreatCategory.AUTONOMY,
        description="Abusing system resources",
        agents=["Executor"],
        mcps=["Infra MCP"],
        scenarios=["S08"]
    ))
    
    # Category 8: Infrastructure (6 threats)
    taxonomy.add_threat(Threat(
        id="IF-01",
        name="Deployment Manipulation",
        category=ThreatCategory.INFRASTRUCTURE,
        description="Manipulating service deployments",
        agents=["Executor"],
        mcps=["Infra MCP"],
        scenarios=["S13"]
    ))
    
    taxonomy.add_threat(Threat(
        id="IF-02",
        name="Config Tampering",
        category=ThreatCategory.INFRASTRUCTURE,
        description="Tampering with system configuration",
        agents=["Executor"],
        mcps=["Infra MCP"],
        scenarios=["S13"]
    ))
    
    taxonomy.add_threat(Threat(
        id="IF-03",
        name="Environment Variable Injection",
        category=ThreatCategory.INFRASTRUCTURE,
        description="Injecting malicious environment variables",
        agents=["Executor"],
        mcps=["Infra MCP"],
        scenarios=["S13"]
    ))
    
    taxonomy.add_threat(Threat(
        id="IF-04",
        name="Container Escape",
        category=ThreatCategory.INFRASTRUCTURE,
        description="Escaping container isolation",
        agents=["Executor"],
        mcps=["Infra MCP"],
        scenarios=["S14"]
    ))
    
    taxonomy.add_threat(Threat(
        id="IF-05",
        name="Privilege Escalation",
        category=ThreatCategory.INFRASTRUCTURE,
        description="Escalating infrastructure privileges",
        agents=["Executor"],
        mcps=["Infra MCP"],
        scenarios=["S13", "S14"]
    ))
    
    taxonomy.add_threat(Threat(
        id="IF-06",
        name="Secret Exposure",
        category=ThreatCategory.INFRASTRUCTURE,
        description="Exposing secrets and credentials",
        agents=["Executor"],
        mcps=["Infra MCP"],
        scenarios=["S12"]
    ))
    
    # Category 9: Visibility (5 threats)
    taxonomy.add_threat(Threat(
        id="V-01",
        name="Log Manipulation",
        category=ThreatCategory.VISIBILITY,
        description="Manipulating audit logs",
        agents=["Monitor"],
        mcps=["Data MCP"],
        scenarios=["S09", "S15"]
    ))
    
    taxonomy.add_threat(Threat(
        id="V-02",
        name="Audit Trail Deletion",
        category=ThreatCategory.VISIBILITY,
        description="Deleting audit trail evidence",
        agents=["Monitor"],
        mcps=["Data MCP"],
        scenarios=["S09"]
    ))
    
    taxonomy.add_threat(Threat(
        id="V-03",
        name="Observability Gaps",
        category=ThreatCategory.VISIBILITY,
        description="Exploiting gaps in observability",
        agents=["Monitor"],
        mcps=["Comms MCP"],
        scenarios=["S15"]
    ))
    
    taxonomy.add_threat(Threat(
        id="V-04",
        name="Detection Evasion",
        category=ThreatCategory.VISIBILITY,
        description="Evading detection mechanisms",
        agents=["All Agents"],
        mcps=["Multiple"],
        scenarios=["S15"]
    ))
    
    taxonomy.add_threat(Threat(
        id="V-05",
        name="Monitoring Blind Spots",
        category=ThreatCategory.VISIBILITY,
        description="Exploiting monitoring blind spots",
        agents=["Monitor"],
        mcps=["Comms MCP"],
        scenarios=["S15"]
    ))
    
    return taxonomy


# Global taxonomy instance
_taxonomy = None


def get_taxonomy() -> ThreatTaxonomy:
    """Get the global taxonomy instance."""
    global _taxonomy
    if _taxonomy is None:
        _taxonomy = create_taxonomy()
    return _taxonomy


def get_threats_by_category(category: ThreatCategory) -> List[Threat]:
    """Get all threats in a category."""
    return get_taxonomy().get_threats_by_category(category)


def get_agents_by_threat(threat_id: str) -> List[str]:
    """Get agents that demonstrate a threat."""
    return get_taxonomy().get_agents_by_threat(threat_id)


def get_scenarios_by_threat(threat_id: str) -> List[str]:
    """Get scenarios that demonstrate a threat."""
    return get_taxonomy().get_scenarios_by_threat(threat_id)


def get_mcps_by_threat(threat_id: str) -> List[str]:
    """Get MCPs involved in a threat."""
    return get_taxonomy().get_mcps_by_threat(threat_id)
