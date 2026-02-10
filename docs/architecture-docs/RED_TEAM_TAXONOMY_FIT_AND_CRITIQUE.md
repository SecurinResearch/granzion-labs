# Red Team Taxonomy Fit and Critique

This document (1) explains **how the Granzion Lab fits red teaming for the Agentic Threats Taxonomy**, and (2) acts as a **critique** with concrete **areas to improve**, including the known issue that the orchestrator agent is not working properly.

---

## Part 1: How the Lab Fits Red Teaming for the Taxonomy

### 1.1 Taxonomy and Lab Purpose

The **Granzion Agentic Threats Taxonomy** (from the CSV and docs) defines **53+ threats across 9 categories**:

1. Instruction  
2. Tool  
3. Memory  
4. Identity & Trust  
5. Orchestration  
6. Communication  
7. Autonomy  
8. Infrastructure  
9. Visibility  

The lab is built to be a **controlled, intentionally vulnerable** target so red teamers can:

- **Exploit** each threat in a repeatable way (via scenarios and agent/MCP interactions).  
- **Observe** concrete state changes (before/after, audit logs, delegation chains, RAG content).  
- **Validate** detection and response (e.g. “did our control catch this?”).

So the lab is a **fit** for red teaming the taxonomy in the sense that:

- **Architecture aligns with taxonomy**: Identity, agents, MCPs, A2A, memory, tools, infra, and observability are all present and mapped to threat categories.  
- **Scenarios map to threats**: 15 scenarios (s01–s15) target specific threat IDs; `threat_coverage.md` reports ~79% of 54 threats testable.  
- **Identity-first**: Many taxonomy threats (impersonation, delegation abuse, weak Agent Cards, A2A forgery) are naturally exercised through the identity and A2A design.  
- **Unified data**: Relational + vector + graph allows testing SQL injection, RAG poisoning, and graph reconnaissance in one environment.  
- **Documented vulnerabilities**: VULNERABILITIES.md and in-code comments tie components to threat IDs, so red teamers know what they are testing.

### 1.2 Where It Fits Well

- **Identity & Trust**: Keycloak, Agent Cards, delegation chains, impersonate MCP, weak verification — strong coverage (s01, s12, s03).  
- **Infrastructure**: Infra MCP (deploy, execute_command, modify_config), s08, s13, s14.  
- **Memory**: Memory MCP and Researcher, RAG and vector store — s02, s06, s10.  
- **Tool**: Data MCP and Infra MCP parameter handling — s04, s08, s13.  
- **Visibility**: Monitor agent gaps, audit log manipulation — s09, s15.  
- **Communication**: Comms MCP (send/receive/broadcast, no encryption) — s03.  
- **Orchestration / Autonomy**: Scenarios s05, s11; design supports workflow hijacking and goal manipulation even if orchestrator behavior is inconsistent (see critique).

### 1.3 Gaps vs Full Taxonomy

- **~21% of threats** not yet testable (e.g. Training Data Poisoning, Dormant Autonomy, Supply Chain — see threat_coverage.md).  
- Some categories (e.g. Communication, Autonomy) have **fewer dedicated scenarios**; coverage is partial.  
- **Rogue Agent Insertion (#25)** and **Coordinated Multi-Agent Attack (#31)** are called out as high-priority gaps.

Overall: the lab **is** a good fit for taxonomy-driven red teaming as a first iteration; the main work is making existing flows reliable and filling coverage gaps.

---

## Part 2: Critique and Areas to Improve

The following is a direct critique: what’s wrong or weak today and what should be improved.

---

### 2.1 Orchestrator Agent Not Working Properly (High)

**Problem**: The Orchestrator is supposed to coordinate multi-agent workflows: route user requests to Researcher (retrieval) or Executor (actions), use A2A (send_message, receive_message, verify_card), and maintain delegation context. In practice it often **does not** reliably:

- **Route** to sub-agents in a single user interaction (e.g. “ask the researcher to find X, then have the executor do Y”).  
- **Call send_message** with correct UUIDs and payloads so that Researcher/Executor actually receive and act on tasks.  
- **Call receive_message** proactively to get sub-agent replies and surface them to the user.  
- **Perform a full A2A handshake** (verify_card then send_message) in one coherent flow.

**Likely causes**:

- **LLM behavior**: The orchestrator is an LLM; it may not consistently choose the right tools in the right order or format (e.g. JSON payload with action/parameters).  
- **Tool interface**: Agno may pass tool arguments in nested structures; `utils.py` has “extreme flattening” and special handling for orchestration keys, suggesting **tool-calling/parsing** is brittle.  
- **Statelessness**: Each request creates a fresh agent; the orchestrator has no persistent memory of prior send_message/receive_message, so multi-turn coordination is hard unless the user re-prompts.  
- **Active A2A delivery**: Comms MCP can call `target_agent.arun(a2a_prompt)` when the target is registered, but the **orchestrator** must first call `send_message` with the right agent ID and message; if it doesn’t, nothing is delivered.  
- **Instructions**: Long, complex instructions may not be followed reliably (e.g. “ALWAYS use UUIDs,” “call receive_message first on follow-ups”).

**Recommendations**:

1. **Stabilize tool wiring**: Ensure Agno consistently passes `to_agent_id` and `message` (and optional `delegation_chain`) into send_message; add integration tests that assert “orchestrator sends → researcher receives and responds.”  
2. **Simplify orchestrator instructions**: Shorter, clearer steps (e.g. “1. For retrieval: call send_message to Researcher UUID … 2. Then call receive_message to get the reply”).  
3. **Add a deterministic orchestration path**: For critical demos, consider a “orchestration mode” that maps intents (e.g. “research X”) to a fixed sequence of MCP calls (send_message to Researcher, then receive_message) so red team scenarios don’t depend on LLM reliability.  
4. **Session or request-scoped context**: Persist “pending A2A message IDs” or last send/receive per request so the orchestrator can be prompted with “you sent X to Researcher; check your mailbox.”  
5. **E2E tests**: Add scenarios that run a user prompt through the orchestrator and assert that Researcher or Executor was invoked and their output is visible (even if only in logs/state).

---

### 2.2 Scenario Execution vs Real Agent Behavior (Medium)

**Problem**: Many scenarios **bypass** the agents and call MCPs or DB directly (e.g. identity_mcp.impersonate, create_delegation, Data MCP). That’s good for **controlled exploitation** but doesn’t prove that an **agent** (e.g. Orchestrator or Executor) would actually do the same thing when prompted.

**Recommendation**: Add at least one or two scenarios per category that **drive an agent via prompt** and then assert on state (e.g. “Send this prompt to Executor; then check that app_data was deleted”). That validates both the vulnerability and the agent’s use of it.

---

### 2.3 Rogue-Inspired TUI Not Delivered (Medium)

**Problem**: Design and requirements describe a Rogue-inspired **TUI** (scenario catalog, execution log, observable state). The implemented interface is **Dashboard (React) + API**. A true terminal TUI is still a task item and would improve operator experience and alignment with the stated “Rogue-inspired” goal.

**Recommendation**: Either implement a minimal TUI (e.g. Python Rich/Textual or similar) that lists scenarios, runs one, and prints before/after and evidence, or explicitly downgrade the requirement to “Dashboard + API only” and update the docs.

---

### 2.4 Coverage Gaps for Taxonomy (Medium)

**Problem**: threat_coverage.md lists **11 threats** as not testable or only partially testable (e.g. Rogue Agent Insertion, Coordinated Multi-Agent Attack, Replay Attacks, Tool Schema Poisoning, Dormant Autonomy, Supply Chain). Some are “out of scope,” but others are high priority and feasible.

**Recommendations**:

- Add **Rogue Agent Insertion** scenario: e.g. onboard an unauthorized agent (weak registration/validation) and show it receiving tasks.  
- Add **Replay** scenario: capture a valid message or token and replay it; assert no replay protection.  
- Add **Coordinated multi-agent** scenario: two agents act in sequence to achieve an outcome (e.g. one exfiltrates, one deletes) to test detection across agents.  
- Document **out-of-scope** threats** clearly (e.g. Training Data Poisoning, Supply Chain) so stakeholders know the lab’s boundaries.

---

### 2.5 Observability and Evidence Quality (Medium)

**Problem**: Audit logs and state capture are present but not always **complete** or **consistent**: e.g. every MCP call might not log identity_context; state_before/state_after might not include graph or RAG state in a comparable way.

**Recommendation**: Define a minimal **evidence schema** (e.g. required fields for each attack step: actor, action, resource, timestamp, identity_context). Ensure all MCPs and critical paths write to it; scenarios then assert on this schema so red team reports are uniform and machine-readable.

---

### 2.6 Keycloak and Token Handling (Lower)

**Problem**: Keycloak automation and token parsing can be brittle (realm not created, wrong issuer, Guest fallback overused). Weak token signing (e.g. for testing IT-03) is documented but could be clearer so red teamers know what they’re testing.

**Recommendation**: Document “expected Keycloak state after full_setup” (realm, client, users, service accounts) and add a health check that verifies at least one user can obtain a token. Add a short “Identity testing” section in DEVELOPER_GUIDE or architecture-docs describing how to use Bearer vs manual context vs Guest for different tests.

---

### 2.7 Property and Unit Test Coverage (Lower)

**Problem**: Property tests exist for many invariants (identity, threat mapping, etc.), but **orchestrator behavior** and **end-to-end scenario success** are not fully covered. Flaky or missing tests make it hard to refactor without regressions.

**Recommendation**: Add property or integration tests that (a) run a small set of scenarios (e.g. s01, s04) and assert success and (b) run the orchestrator with a fixed prompt and assert that at least one send_message or receive_message was called (or that a sub-agent was invoked). This protects the “red team readiness” of the lab.

---

## Part 3: Prioritized Improvement List

| Priority | Area | Action |
|----------|------|--------|
| **P0** | Orchestrator reliability | Fix tool wiring and instructions; add deterministic path or E2E test so “orchestrator → researcher/executor” works consistently. |
| **P1** | Scenario vs agent behavior | Add at least 1–2 scenarios per major category that drive agents by prompt and assert on state. |
| **P1** | Taxonomy coverage | Add scenarios for Rogue Agent Insertion, Replay, and (if feasible) Coordinated multi-agent; document out-of-scope. |
| **P2** | TUI | Implement minimal Rogue-inspired TUI or update docs to “Dashboard + API only.” |
| **P2** | Evidence schema | Standardize audit/evidence fields and ensure MCPs and scenarios use them. |
| **P3** | Keycloak/docs | Document expected Keycloak state and identity testing; improve health checks. |
| **P3** | Tests | Add E2E or property tests for orchestrator and for scenario success. |

---

## Summary

- The lab **is a fit** for red teaming the Agentic Threats Taxonomy: identity-first design, 15 scenarios, ~79% threat coverage, and documented vulnerabilities.  
- The **main blocker** for “lab that works for everyone” is the **orchestrator not working properly**; fixing that and adding a few scenario and coverage improvements will make the lab significantly more convincing and usable.  
- Addressing the items above in priority order will move the lab from “basic but promising” to “production-ready for red team exercises” against the taxonomy.
