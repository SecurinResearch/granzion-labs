# Threat Taxonomy Coverage Analysis

## Threat ID formats

- **Taxonomy IDs**: Numeric **1–54** (used in this document and in some scenarios, e.g. S16 uses `37` for Replay).
- **Legacy codes**: Category prefix + number (e.g. **IT-01**, **M-02**, **C-03**). Used in scenario `threat_ids` and in [VULNERABILITIES.md](VULNERABILITIES.md). Map to the same taxonomy categories (Identity & Trust, Memory, Communication, etc.).

Scenarios may use either format. CI checks that every scenario `threat_id` is either a taxonomy ID (1–54) or a valid legacy code pattern.

## Agent-driven vs direct MCP/DB

| Type | Description |
|------|-------------|
| **Agent-driven** | Scenario sends a **prompt** to an agent via the API (`POST /agents/{id}/run`), runs the agent, then asserts on **state** (DB, audit log, or messages) that the expected bad outcome occurred. Proves the vulnerability is exploitable *through the agent*. |
| **Direct MCP/DB** | Scenario calls MCPs or DB directly (e.g. `identity_mcp.impersonate`, `create_delegation`, Data MCP). Proves the vulnerability exists but does not prove an agent would do the same when prompted. |

| Scenario | Category | Type |
|----------|----------|------|
| S01 | Identity & Trust | Direct MCP/DB |
| S02 | Memory | Direct MCP/DB |
| S03 | Communication | Direct MCP/DB |
| S04 | Tool | Direct MCP/DB |
| S05 | Orchestration | Direct MCP/DB |
| S06 | Memory | Direct MCP/DB |
| S07 | Instruction | Direct MCP/DB |
| S08 | Infrastructure | Direct MCP/DB |
| S09 | Visibility | Direct MCP/DB |
| S10 | Memory | Direct MCP/DB |
| S11 | Autonomy | Direct MCP/DB |
| S12 | Identity & Trust | Direct MCP/DB |
| S13 | Infrastructure | Direct MCP/DB |
| S14 | Infrastructure | Direct MCP/DB |
| S15 | Visibility | Direct MCP/DB |
| S16 | Communication | Direct MCP/DB |
| S17 | Orchestration | **Agent-driven** |

## Summary

Analysis of the 54 threats across 9 categories against the Granzion Lab's 15 scenarios and architecture.

---

## Coverage Matrix

| Category | Threats | Lab Scenarios | Coverage |
|----------|---------|---------------|----------|
| 1. Instruction | 4 | s07, s11 | **50%** |
| 2. Tool | 5 | s04, s08 | **40%** |
| 3. Memory | 7 | s02, s06, s10 | **43%** |
| 4. Identity & Trust | 9 | s01, s12 | **67%** |
| 5. Orchestration | 7 | s05, s11 | **43%** |
| 6. Communication | 6 | s03 | **33%** |
| 7. Autonomy | 4 | s11 | **25%** |
| 8. Infrastructure | 5 | s08, s13, s14 | **60%** |
| 9. Visibility | 7 | s09, s15 | **43%** |

**Overall: 43/54 threats testable (79%)**

---

## Detailed Mapping

### 1. Instruction Threats (4)
| # | Threat | Testable | Scenario | Notes |
|---|--------|----------|----------|-------|
| 1 | Goal & Mission Manipulation | ✅ | s11 | Goal Manipulation scenario |
| 2 | Prompt Injection | ✅ | s07 | LiteLLM jailbreaking |
| 3 | Semantic Exploitation | ⚠️ | - | Through agent instructions |
| 4 | Instruction-Level Jailbreaks | ✅ | s07 | LiteLLM jailbreaking |

### 2. Tool Threats (5)
| # | Threat | Testable | Scenario | Notes |
|---|--------|----------|----------|-------|
| 5 | Unauthorized Tool Invocation | ✅ | s04 | Tool param injection |
| 6 | Unsafe Tool Parameters | ✅ | s04 | Parameter injection |
| 7 | Tool Data Exfiltration | ✅ | s12 | Credential theft |
| 9 | Tool Schema Poisoning | ⚠️ | - | MCP tool definitions |
| 10 | Over-Privileged Tools | ✅ | s13 | Privilege escalation |

### 3. Memory Threats (7)
| # | Threat | Testable | Scenario | Notes |
|---|--------|----------|----------|-------|
| 11 | Persistent Memory Poisoning | ✅ | s02 | Memory poisoning |
| 12 | Training Data Poisoning | ❌ | - | Out of scope |
| 13 | Session Memory Manipulation | ✅ | s06 | Context stuffing |
| 14 | Cross-Session Contamination | ✅ | s10 | Cross-agent memory |
| 15 | State Reasoning Corruption | ⚠️ | s11 | Goal manipulation |
| 16 | Vector Store Poisoning | ✅ | s02 | pgvector poisoning |
| 17 | Memory Exfiltration | ✅ | s10 | Cross-agent read |

### 4. Identity & Trust Threats (9)
| # | Threat | Testable | Scenario | Notes |
|---|--------|----------|----------|-------|
| 18 | Agent Impersonation | ✅ | s01 | IT-02 vulnerability |
| 19 | Implicit Trust Abuse | ✅ | s01 | Delegation trust |
| 20 | Endpoint Spoofing | ✅ | s03 | A2A Discovery endpoint |
| 21 | Auth Mechanism Failures | ✅ | s01 | Weak token validation |
| 22 | Authorization Failures | ✅ | s01, s13 | Permission escalation |
| 23 | Credential Abuse | ✅ | s12 | Credential theft |
| 24 | Consent Bypass | ✅ | - | IT-04 no checks |
| 25 | Rogue Agent Insertion | ⚠️ | - | onboarding scenario |
| 26 | Agent Card Abuse | ✅ | s03 | IT-07, IT-08 |

### 5. Orchestration Threats (7)
| # | Threat | Testable | Scenario | Notes |
|---|--------|----------|----------|-------|
| 27 | Agent Selection Manipulation | ⚠️ | s05 | Workflow hijacking |
| 28 | Task Delegation Corruption | ✅ | s05 | Workflow hijacking |
| 29 | Session Orchestration Hijack | ✅ | s05 | Live session |
| 30 | Delegated Trust Chain Abuse | ✅ | s01 | Delegation chain |
| 31 | Coordinated Multi-Agent Attack | ⚠️ | - | 4 agents available |
| 32 | Blast Radius Amplification | ⚠️ | - | Cascading |
| 33 | Adaptive Mission Retargeting | ✅ | s11 | Goal manipulation |

### 6. Communication Threats (6)
| # | Threat | Testable | Scenario | Notes |
|---|--------|----------|----------|-------|
| 34 | Message Manipulation | ✅ | s03 | A2A forgery |
| 35 | Trust Boundary Confusion | ✅ | s03 | Channel mixing |
| 36 | Session Token Compromise | ✅ | s12 | Token theft |
| 37 | Replay Attacks | ✅ | s16 | No replay protection; S16 replays A2A message |
| 38 | Covert Instruction Staging | ⚠️ | s06 | Multi-turn |
| 39 | Peer Coordination Abuse | ⚠️ | s03 | Broadcast abuse |

### 7. Autonomy Threats (4)
| # | Threat | Testable | Scenario | Notes |
|---|--------|----------|----------|-------|
| 40 | Rogue Autonomous Behavior | ⚠️ | s11 | Goal manipulation |
| 41 | Adaptive Autonomy | ⚠️ | - | Would need monitor |
| 42 | Dormant Autonomy | ❌ | - | Needs async execution |
| 43 | Safety Control Bypass | ✅ | s15 | Detection evasion |

### 8. Infrastructure Threats (5)
| # | Threat | Testable | Scenario | Notes |
|---|--------|----------|----------|-------|
| 44 | Resource Exhaustion | ✅ | s08 | Unauthorized infra |
| 45 | Network Manipulation | ⚠️ | - | Docker network |
| 46 | Protocol Exploitation | ⚠️ | s14 | Container boundary |
| 47 | Supply Chain Compromise | ❌ | - | Out of scope |
| 48 | Runtime Compromise | ✅ | s14 | Container escape |

### 9. Visibility Threats (7)
| # | Threat | Testable | Scenario | Notes |
|---|--------|----------|----------|-------|
| 49 | Action Untraceability | ✅ | s09 | Audit manipulation |
| 50 | Opaque Decision-Making | ⚠️ | - | No explainability |
| 51 | Gradual Compromise | ✅ | s15 | Detection evasion |
| 52 | Cross-Protocol Gaps | ⚠️ | - | MCP/A2A mixing |
| 53 | Sensitive Data Exposure | ✅ | s12 | Credential leakage |
| 54 | Consent Audit Failures | ✅ | s09 | No consent tracking |

---

## Legend
- ✅ **Fully testable** with existing scenarios
- ⚠️ **Partially testable** or requires minor additions
- ❌ **Not testable** (out of scope for this lab)

---

## Gaps to Address

### High Priority (easy to add)
1. **Rogue Agent Insertion (#25)** - Add onboarding scenario
2. **Coordinated Attack (#31)** - Multi-agent coordination test
3. **Replay Attacks (#37)** - Add explicit scenario

### Medium Priority
4. Endpoint Spoofing (#20)
5. Agent Card Abuse (#26)
6. Network Manipulation (#45)

### Out of Scope
7. Training Data Poisoning (#12) - Requires fine-tuning
8. Dormant Autonomy (#42) - Needs long-running async
9. Supply Chain (#47) - External dependencies

See [LAB_BOUNDARIES.md](LAB_BOUNDARIES.md) for the full out-of-scope list and rationale.
