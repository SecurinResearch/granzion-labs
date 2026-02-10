"""
Property tests for threat taxonomy coverage.

These tests validate that the threat taxonomy has complete coverage across
all categories, agents, MCPs, and scenarios.
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.taxonomy import get_taxonomy, ThreatCategory
from src.api.threat_api import get_threat_api


# Feature: granzion-lab-simplified, Property 6: Threat category mapping completeness
@settings(max_examples=100)
@given(
    category=st.sampled_from(list(ThreatCategory))
)
@pytest.mark.property_test
def test_property_6_threat_category_mapping_completeness(category):
    """
    Property 6: Threat category mapping completeness
    
    For any threat category from the 9 taxonomy categories, the system should
    return at least one agent and one scenario that demonstrates threats in
    that category.
    
    Validates: Requirements 2.2, 10.4
    """
    api = get_threat_api()
    
    # Get threats in this category
    threats = api.get_threats_by_category(category.value)
    
    # Category must have at least one threat
    assert len(threats) > 0, f"Category {category.value} has no threats"
    
    # Collect all agents and scenarios for this category
    all_agents = set()
    all_scenarios = set()
    
    for threat in threats:
        all_agents.update(threat["agents"])
        all_scenarios.update(threat["scenarios"])
    
    # Category must have at least one agent
    assert len(all_agents) > 0, f"Category {category.value} has no agents"
    
    # Category must have at least one scenario
    assert len(all_scenarios) > 0, f"Category {category.value} has no scenarios"


# Feature: granzion-lab-simplified, Property 7: Bidirectional threat-component mapping
@settings(max_examples=100)
@given(
    threat_id=st.sampled_from([
        "I-01", "I-02", "I-03", "I-04", "I-05",
        "T-01", "T-02", "T-03", "T-04", "T-05",
        "M-01", "M-02", "M-03", "M-04", "M-05",
        "IT-01", "IT-02", "IT-03", "IT-04", "IT-05", "IT-06",
        "O-01", "O-02", "O-03", "O-04", "O-05",
        "C-01", "C-02", "C-03", "C-04", "C-05",
        "A-01", "A-02", "A-03", "A-04", "A-05",
        "IF-01", "IF-02", "IF-03", "IF-04", "IF-05", "IF-06",
        "V-01", "V-02", "V-03", "V-04", "V-05",
    ])
)
@pytest.mark.property_test
def test_property_7_bidirectional_threat_component_mapping(threat_id):
    """
    Property 7: Bidirectional threat-component mapping
    
    For any agent, querying the system should return which threat categories
    it demonstrates, and for any threat category, querying should return which
    agents demonstrate it.
    
    Validates: Requirements 10.3, 10.4
    """
    api = get_threat_api()
    taxonomy = get_taxonomy()
    
    # Get threat details
    threat = taxonomy.get_threat(threat_id)
    assert threat is not None, f"Threat {threat_id} not found"
    
    # Forward mapping: threat -> agents
    agents = api.get_agents_by_threat(threat_id)
    assert len(agents) > 0, f"Threat {threat_id} has no agents"
    
    # Backward mapping: agent -> threats
    for agent in agents:
        if agent == "All Agents":
            continue  # Skip generic "All Agents"
        
        agent_threats = api.get_threats_by_agent(agent)
        threat_ids = [t["id"] for t in agent_threats]
        
        # The original threat should be in the agent's threats
        assert threat_id in threat_ids, f"Agent {agent} doesn't list threat {threat_id}"
    
    # Forward mapping: threat -> scenarios
    scenarios = api.get_scenarios_by_threat(threat_id)
    assert len(scenarios) > 0, f"Threat {threat_id} has no scenarios"
    
    # Backward mapping: scenario -> threats
    for scenario in scenarios:
        scenario_threats = api.get_threats_by_scenario(scenario)
        threat_ids = [t["id"] for t in scenario_threats]
        
        # The original threat should be in the scenario's threats
        assert threat_id in threat_ids, f"Scenario {scenario} doesn't list threat {threat_id}"


def test_all_53_threats_exist():
    """Test that all 53 threats are defined in the taxonomy."""
    taxonomy = get_taxonomy()
    
    # Should have exactly 53 threats
    assert len(taxonomy.threats) == 53, f"Expected 53 threats, got {len(taxonomy.threats)}"


def test_all_9_categories_have_threats():
    """Test that all 9 categories have at least one threat."""
    api = get_threat_api()
    
    for category in ThreatCategory:
        threats = api.get_threats_by_category(category.value)
        assert len(threats) > 0, f"Category {category.value} has no threats"


def test_all_threats_have_agents():
    """Test that all threats have at least one agent assigned."""
    taxonomy = get_taxonomy()
    
    for threat_id, threat in taxonomy.threats.items():
        assert len(threat.agents) > 0, f"Threat {threat_id} has no agents"


def test_all_threats_have_mcps():
    """Test that all threats have at least one MCP assigned."""
    taxonomy = get_taxonomy()
    
    for threat_id, threat in taxonomy.threats.items():
        assert len(threat.mcps) > 0, f"Threat {threat_id} has no MCPs"


def test_all_threats_have_scenarios():
    """Test that all threats have at least one scenario assigned."""
    taxonomy = get_taxonomy()
    
    for threat_id, threat in taxonomy.threats.items():
        assert len(threat.scenarios) > 0, f"Threat {threat_id} has no scenarios"


def test_coverage_stats():
    """Test that coverage statistics are complete."""
    api = get_threat_api()
    stats = api.get_coverage_stats()
    
    # Should have all expected fields
    assert "total_threats" in stats
    assert "threats_by_category" in stats
    assert "threats_with_scenarios" in stats
    assert "threats_with_agents" in stats
    assert "threats_with_mcps" in stats
    assert "unique_agents" in stats
    assert "unique_mcps" in stats
    assert "unique_scenarios" in stats
    
    # All threats should have coverage
    assert stats["total_threats"] == 53
    assert stats["threats_with_scenarios"] == 53
    assert stats["threats_with_agents"] == 53
    assert stats["threats_with_mcps"] == 53


def test_category_coverage():
    """Test that category coverage is complete."""
    api = get_threat_api()
    coverage = api.get_category_coverage()
    
    # Should have coverage for all 9 categories
    assert len(coverage) == 9
    
    for category, details in coverage.items():
        # Each category should have threats
        assert details["threat_count"] > 0, f"Category {category} has no threats"
        
        # Each category should have agents
        assert len(details["agents"]) > 0, f"Category {category} has no agents"
        
        # Each category should have scenarios
        assert len(details["scenarios"]) > 0, f"Category {category} has no scenarios"
        
        # Each category should have MCPs
        assert len(details["mcps"]) > 0, f"Category {category} has no MCPs"


def test_validate_complete_coverage():
    """Test that all threats have complete coverage."""
    api = get_threat_api()
    validation = api.validate_complete_coverage()
    
    # Should be complete
    assert validation["complete"], f"Coverage incomplete: {validation['issues']}"
    assert validation["total_threats"] == 53
    assert validation["threats_with_issues"] == 0
    assert len(validation["issues"]) == 0


def test_threat_ids_follow_convention():
    """Test that all threat IDs follow the naming convention."""
    taxonomy = get_taxonomy()
    
    # Expected prefixes for each category
    category_prefixes = {
        ThreatCategory.INSTRUCTION: "I-",
        ThreatCategory.TOOL: "T-",
        ThreatCategory.MEMORY: "M-",
        ThreatCategory.IDENTITY_TRUST: "IT-",
        ThreatCategory.ORCHESTRATION: "O-",
        ThreatCategory.COMMUNICATION: "C-",
        ThreatCategory.AUTONOMY: "A-",
        ThreatCategory.INFRASTRUCTURE: "IF-",
        ThreatCategory.VISIBILITY: "V-",
    }
    
    for threat_id, threat in taxonomy.threats.items():
        expected_prefix = category_prefixes[threat.category]
        assert threat_id.startswith(expected_prefix), \
            f"Threat {threat_id} in category {threat.category.value} should start with {expected_prefix}"


def test_all_scenarios_referenced():
    """Test that all 15 scenarios are referenced in the taxonomy."""
    taxonomy = get_taxonomy()
    
    expected_scenarios = [
        "S01", "S02", "S03", "S04", "S05",
        "S06", "S07", "S08", "S09", "S10",
        "S11", "S12", "S13", "S14", "S15"
    ]
    
    # Collect all scenarios from threats
    all_scenarios = set()
    for threat in taxonomy.threats.values():
        all_scenarios.update(threat.scenarios)
    
    # All expected scenarios should be referenced
    for scenario in expected_scenarios:
        assert scenario in all_scenarios, f"Scenario {scenario} not referenced in taxonomy"


def test_all_agents_referenced():
    """Test that all 4 agents are referenced in the taxonomy."""
    taxonomy = get_taxonomy()
    
    expected_agents = ["Orchestrator", "Researcher", "Executor", "Monitor"]
    
    # Collect all agents from threats
    all_agents = set()
    for threat in taxonomy.threats.values():
        all_agents.update(threat.agents)
    
    # All expected agents should be referenced
    for agent in expected_agents:
        assert agent in all_agents or "All Agents" in all_agents, \
            f"Agent {agent} not referenced in taxonomy"


def test_all_mcps_referenced():
    """Test that all 5 MCPs are referenced in the taxonomy."""
    taxonomy = get_taxonomy()
    
    expected_mcps = ["Identity MCP", "Memory MCP", "Data MCP", "Comms MCP", "Infra MCP"]
    
    # Collect all MCPs from threats
    all_mcps = set()
    for threat in taxonomy.threats.values():
        all_mcps.update(threat.mcps)
    
    # All expected MCPs should be referenced
    for mcp in expected_mcps:
        assert mcp in all_mcps or "All MCPs" in all_mcps or "Multiple" in all_mcps, \
            f"MCP {mcp} not referenced in taxonomy"
