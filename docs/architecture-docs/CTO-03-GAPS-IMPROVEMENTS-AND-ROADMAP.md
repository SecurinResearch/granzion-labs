# CTO Brief — Part 3: Gaps, Improvements, and Roadmap

**Audience:** CTO / leadership  
**Purpose:** Complete list of what must be improved or built, in priority order, with rationale and concrete actions. Use this to decide what to fund and in what sequence.  
**Companion docs:** Part 1 (executive summary), Part 2 (diagrams explained).

---

## How This Document Is Organized

1. **P0 (Critical):** Blockers for “lab that works” for demos and red team exercises — must fix first.
2. **P1 (High):** Important for credibility and taxonomy coverage — do next.
3. **P2 (Medium):** Improves usability and consistency — do after P1.
4. **P3 (Lower):** Polish, docs, and long-term maintainability — do when capacity allows.
5. **Out of scope / known limits:** What we explicitly do not do in this lab.
6. **Suggested roadmap:** Phasing and dependencies for CTO planning.

Every item includes: **what’s wrong or missing**, **why it matters**, **concrete action(s)**, and **how to verify** when done.

---

# P0 — Critical (Must Fix First)

---

## P0-1. Orchestrator Agent Reliability

**What’s wrong:** The Orchestrator is supposed to coordinate multi-agent workflows: route user requests to Researcher (retrieval) or Executor (actions), use A2A (send_message, receive_message, verify_card), and maintain delegation context. In practice it **does not reliably**:
- Route to sub-agents in a single user interaction (e.g. “ask the researcher to find X, then have the executor do Y”).
- Call send_message with correct agent UUIDs and payloads so Researcher/Executor actually receive and act.
- Call receive_message to get sub-agent replies and surface them to the user.
- Perform a full A2A handshake (verify_card then send_message) in one coherent flow.

**Why it matters:** Without this, we cannot demonstrate multi-agent coordination or A2A in a demo. Red team scenarios that assume “orchestrator delegates to executor” cannot be proven via natural-language prompts. It is the **single biggest blocker** for CTO/stakeholder demos.

**Root causes (concise):**
- LLM non-determinism: the orchestrator may not choose the right tools in the right order or format.
- Tool wiring: Agno may pass arguments in nested structures; `src/agents/utils.py` has “extreme flattening” and special handling, suggesting brittle tool-calling/parsing.
- Statelessness: each request creates a fresh agent; no persistent memory of prior send_message/receive_message, so multi-turn coordination is hard unless the user re-prompts.
- The orchestrator must *choose* to call send_message; if it doesn’t, Comms MCP never gets a chance to trigger the target agent.

**Concrete actions:**
1. **Stabilize tool wiring:** Ensure Agno consistently passes `to_agent_id` and `message` (and optional `delegation_chain`) into send_message. Add integration test: “orchestrator sends message to Researcher UUID → Researcher receives and responds.”
2. **Simplify orchestrator instructions:** Shorten and clarify (e.g. “1. For retrieval: call send_message to Researcher UUID … 2. Then call receive_message to get the reply”). Consider few-shot examples in the system prompt.
3. **Add a deterministic orchestration path (recommended):** For critical demos, implement an “orchestration mode” or intent router that maps intents (e.g. “research X”, “execute Y”) to a fixed sequence of MCP calls (send_message to Researcher/Executor, then receive_message) so demos don’t depend on LLM reliability.
4. **Session or request-scoped context:** Persist “pending A2A message IDs” or last send/receive per request so the orchestrator can be prompted with “you sent X to Researcher; check your mailbox” on follow-up.
5. **E2E test:** Add a test that runs a fixed user prompt through the orchestrator and asserts that at least one send_message (or receive_message) was called and that a sub-agent was invoked (e.g. via Comms MCP or DB state).

**Verify when done:** (a) E2E test passes. (b) Manual test: “Ask the researcher to search memory for policies” results in Researcher being invoked and a reply visible (in response or in receive_message). (c) Same for Executor for a simple action.

**Ownership / effort:** Engineering (backend/agents). Estimate: 1–2 sprints for full fix; 0.5 sprint for deterministic path + E2E test as a stopgap.

---

# P1 — High (Do Next)

---

## P1-1. Scenario–Agent Linkage (Prove Agents Do the Attack)

**What’s wrong:** Most scenarios **bypass** agents and call MCPs or DB directly (e.g. identity_mcp.impersonate, create_delegation, Data MCP). That proves the *vulnerability* exists but does **not** prove that an *agent* would perform the same action when prompted. For CTO and customers we need to show “when you prompt the agent like this, it does the bad thing.”

**Why it matters:** Red team value is higher when we demonstrate that the vulnerability is exploitable *through the agent*, not only via direct API/MCP calls. It also validates that our agent instructions and tool wiring don’t accidentally mitigate the vulnerability.

**Concrete actions:**
1. Add at least **one scenario per major threat category** (Identity, Tool, Memory, Orchestration, Communication, Infrastructure, Visibility) that: (a) sends a **prompt** to an agent (Orchestrator or Executor or Researcher as appropriate), (b) runs the agent, (c) asserts on **state** (DB, audit log, or message) that the expected bad outcome occurred.
2. Document which scenarios are “direct MCP/DB” vs “agent-driven” in threat_coverage.md or scenario README.

**Verify when done:** For each such scenario: run it, then inspect state; confirm the agent (not only the scenario script) performed the action that led to the state change.

**Effort:** ~1 scenario per category (e.g. 6–7 scenarios); reuse existing vulnerabilities. Estimate: 0.5–1 sprint.

---

## P1-2. Taxonomy Coverage Gaps (New Scenarios)

**What’s wrong:** threat_coverage.md lists **11 threats** as not testable or only partially testable. Some are out of scope; others are high priority and feasible:
- **Rogue Agent Insertion (#25):** No scenario that demonstrates an unauthorized agent joining and receiving tasks.
- **Replay Attacks (#37):** No explicit scenario that captures a valid message or token and replays it to show lack of replay protection.
- **Coordinated Multi-Agent Attack (#31):** No scenario where two agents act in sequence to achieve an outcome (e.g. one exfiltrates, one deletes) to test detection across agents.
- **Tool Schema Poisoning (#9):** Only partially testable (MCP tool definitions); could add a scenario that poisons or abuses tool schema.
- Others (e.g. Dormant Autonomy #42, Supply Chain #47) may be out of scope — see below.

**Why it matters:** To claim “we cover the taxonomy” we need to close the most important testable gaps and clearly document what we do not cover.

**Concrete actions:**
1. **Rogue Agent Insertion:** Add scenario (e.g. s16) that: weak registration/onboarding or validation, onboard an unauthorized agent, show it receives tasks (e.g. via send_message or task queue). Map to threat #25.
2. **Replay:** Add scenario that: capture a valid A2A message or token, replay it, assert that the system accepts it (no replay protection). Map to #37.
3. **Coordinated multi-agent:** Add scenario that: two agents (e.g. Researcher + Executor) act in sequence (e.g. one retrieves sensitive data, one deletes or exfiltrates); assert on combined state; document for detection testing. Map to #31.
4. **Out-of-scope document:** In threat_coverage.md or a short “Lab boundaries” doc, list threats we explicitly do not test (e.g. Training Data Poisoning #12, Dormant Autonomy #42, Supply Chain #47) and why (e.g. requires fine-tuning, long-running async, external dependencies).

**Verify when done:** New scenarios run and pass; threat_coverage.md updated; out-of-scope list agreed and published.

**Effort:** ~0.5 sprint for the three high-priority scenarios; 0.25 for doc.

---

## P1-3. Evidence and Observability Consistency

**What’s wrong:** Audit logs and state_before/state_after exist but are not always **complete** or **consistent**: not every MCP call may log identity_context; state capture may not include graph or RAG state in a comparable way across scenarios; there is no single **evidence schema** for red team reports.

**Why it matters:** For CTO and compliance we need uniform, machine-readable evidence: “who did what, when, with what identity.” Inconsistent or missing fields make it hard to automate reporting and to prove attribution.

**Concrete actions:**
1. **Define a minimal evidence schema:** Required fields for each attack step or tool call: e.g. actor (user_id, agent_id), action (tool name or operation), resource (e.g. table, message id), timestamp, identity_context (or key fields). Document in docs (e.g. EVIDENCE_SCHEMA.md).
2. **Ensure all MCPs and critical paths write to it:** Audit logger or a dedicated evidence logger that every MCP tool call (and key API paths) uses. Optionally store in a dedicated `evidence` or structured `audit_log` table.
3. **Scenarios assert on schema:** Where relevant, scenario criteria check that expected evidence entries exist and contain required fields.
4. **State capture:** Ensure state_before/state_after for scenarios that need it include graph and RAG state (e.g. delegation count from graph, top-k memory entries) so before/after is comparable.

**Verify when done:** (a) Schema doc exists. (b) Sample scenario run produces evidence that conforms. (c) At least one scenario asserts on evidence structure.

**Effort:** ~0.5 sprint.

---

# P2 — Medium (After P1)

---

## P2-1. Rogue-Inspired TUI (Or Explicitly Drop It)

**What’s wrong:** Design and requirements describe a **Rogue-inspired TUI** (scenario catalog, execution log, observable state). The only delivered interface is **Dashboard (React) + API**. A true terminal TUI is still a task item.

**Why it matters:** Either we deliver on the stated “Rogue-inspired” UX (which some operators prefer for terminals) or we explicitly scope down to “Dashboard + API only” and update all docs and requirements so we don’t over-promise.

**Concrete actions (choose one):**
- **Option A — Implement minimal TUI:** Build a minimal TUI (e.g. Python Rich or Textual) that: lists scenarios (s01–s15), allows selecting and running one, prints execution log and before/after state and evidence. Integrate with existing API (e.g. POST /scenarios/{id}/run, GET /logs). Document in QUICKSTART.
- **Option B — Downgrade requirement:** Update requirements.md, design.md, and any CTO-facing docs to state “Primary interface: Dashboard + API. TUI is out of scope for current release.” Remove or defer the “Implement Rogue-inspired TUI” task.

**Verify when done:** Either (a) TUI runs and can execute at least one scenario and show result, or (b) Docs and task list no longer promise TUI.

**Effort:** Option A ~0.5–1 sprint; Option B ~0.25 sprint (docs + task list).

---

## P2-2. Keycloak and Identity Testing Clarity

**What’s wrong:** Keycloak automation and token parsing can be brittle (realm not created, wrong issuer, Guest fallback overused). Weak token signing (e.g. for testing IT-03) is documented but could be clearer. There is no single place that describes “expected Keycloak state after full_setup” and “how to use Bearer vs manual context vs Guest for different tests.”

**Why it matters:** Red teamers and QA need to know exactly what identity configuration to expect and how to test with different identity modes. Reduces support and confusion.

**Concrete actions:**
1. **Document expected Keycloak state:** After full_setup: realm name, client id(s), list of users (Alice, Bob, Charlie) and their roles, service accounts (sa-orchestrator, etc.), and how to obtain a token (e.g. via Keycloak UI or token endpoint). Put in docs/architecture-docs or keycloak-automation.md.
2. **Health check:** Add a health check (e.g. in /health or a separate /health/identity) that verifies: (a) Keycloak is reachable, (b) realm exists, (c) at least one user can obtain a token (optional but valuable). If (c) fails, return degraded with a clear message.
3. **Identity testing section:** Short section in DEVELOPER_GUIDE or architecture-docs: “Identity testing: Bearer token (real user), manual context (testing as a specific user/agent), Guest (unauthenticated). When to use each and example request bodies.”

**Verify when done:** Doc is reviewable; health check returns expected status; red teamer can follow the section to run tests with each identity mode.

**Effort:** ~0.25 sprint.

---

## P2-3. Property and E2E Test Coverage

**What’s wrong:** Property tests exist for many invariants (identity, threat mapping, etc.), but **orchestrator behavior** and **end-to-end scenario success** are not fully covered. Flaky or missing tests make refactoring risky.

**Why it matters:** Prevents regressions when we fix the orchestrator or add scenarios; gives confidence that “red team readiness” is maintained.

**Concrete actions:**
1. **Orchestrator E2E (or integration):** Test that: with a fixed prompt (e.g. “Send a message to the Researcher asking for a summary of policies”), the orchestrator’s run results in at least one call to send_message (or receive_message), or that the Researcher agent was invoked (e.g. via Comms MCP or DB message table). Can be mocked for speed if needed.
2. **Scenario success tests:** Add a test (or CI job) that runs a small fixed set of scenarios (e.g. s01, s04, s07) and asserts that they complete and report success (or expected failure). Protects against regressions in scenario engine or MCPs.

**Verify when done:** CI runs the new tests; they pass on main. Any change that breaks orchestrator flow or scenario execution fails the test.

**Effort:** ~0.25–0.5 sprint.

---

# P3 — Lower (When Capacity Allows)

---

## P3-1. Documentation and Onboarding

**What’s wrong:** We have many docs (architecture, workflow, components, diagrams, CTO briefs) but no single “start here” path for a new engineer or red teamer. QUICKSTART exists but could tie more clearly to identity and diagram set.

**Concrete actions:** Add or update a “Lab onboarding” page (or section in README) that: (1) points to QUICKSTART for runbook, (2) points to CTO-01/02/03 for leadership overview, (3) points to ARCHITECTURE_DIAGRAM and WORKFLOW_DIAGRAM plus CTO-02 for diagrams, (4) points to Identity testing (P2-2) and scenario list. Keep it to one page with links.

**Effort:** ~0.25 sprint.

---

## P3-2. Vulnerability and Threat ID Consistency

**What’s wrong:** Vulnerabilities are documented in VULNERABILITIES.md and in-code comments; threat IDs are in threat_coverage and taxonomy. Small risk of drift (e.g. wrong ID in a comment, or scenario not updated when threat list changes).

**Concrete actions:** (1) One-time pass: ensure every scenario file and every VULNERABILITIES.md entry uses the same threat ID convention (e.g. from taxonomy CSV). (2) Add a small script or property test that checks that every scenario’s threat_ids appear in the taxonomy and that every documented vulnerability has a threat ID. Run in CI.

**Effort:** ~0.25 sprint.

---

## P3-3. Dashboard and API Polish

**What’s wrong:** Dashboard and API are functional but could be polished for CTO demos: e.g. clearer scenario result view (before/after diff, evidence list), clearer identity display in agent chat response, or a simple “run all scenarios” button with summary pass/fail.

**Concrete actions:** Prioritize 2–3 UX improvements: (a) Scenario result: show state diff and evidence in a readable layout. (b) Agent response: show “acting as” (user/agent) and delegation chain. (c) Optional: “Run all” with summary. Implement in frontend and optionally extend API if needed.

**Effort:** ~0.5 sprint.

---

# Out of Scope / Known Limits

**Explicitly not in scope for this lab (document these so CTO and stakeholders know):**

| Topic | Reason |
|-------|--------|
| **Training / fine-tuning data poisoning (#12)** | Requires model fine-tuning pipeline; out of scope for a runtime lab. |
| **Dormant autonomy (#42)** | Requires long-running async execution and delayed triggers; not modeled in current agent lifecycle. |
| **Supply chain (#47)** | External dependencies (e.g. poisoned packages); not in current threat surface. |
| **Production-grade security** | Lab is intentionally vulnerable; no intention to harden for production. |
| **Full Rogue parity** | We took inspiration (scenario-driven, observable outcomes); we do not implement Rogue’s evaluation engine or TUI. |
| **Full 54/54 threat coverage** | 79% testable today; some threats are out of scope or low priority; we aim to close high-priority gaps (P1-2) and document the rest. |

**Action:** Add a short “Lab boundaries” or “Out of scope” section to threat_coverage.md or a dedicated doc, and reference it from CTO-01.

---

# Suggested Roadmap (Phasing for CTO)

**Phase 1 (P0) — “Lab works for demos” (1–2 sprints)**  
- P0-1: Orchestrator reliability (deterministic path + E2E test as first step; full LLM reliability as follow-up).  
- Outcome: Orchestrator → Researcher/Executor flow works reliably at least in “orchestration mode” or fixed prompts; E2E test in CI.

**Phase 2 (P1) — “Credible red team and taxonomy” (1–1.5 sprints)**  
- P1-1: At least one agent-driven scenario per major category.  
- P1-2: New scenarios for Rogue Agent Insertion, Replay, Coordinated multi-agent; out-of-scope doc.  
- P1-3: Evidence schema and consistent audit/evidence logging.  
- Outcome: Red team can show “agent did the bad thing”; taxonomy gaps reduced; evidence is structured.

**Phase 3 (P2) — “Usable and maintainable” (0.75–1.25 sprints)**  
- P2-1: TUI (minimal) or explicit “Dashboard + API only” scope.  
- P2-2: Keycloak and identity testing docs + health check.  
- P2-3: Orchestrator and scenario E2E/property tests in CI.  
- Outcome: Clear interface scope; identity testing is documented; CI protects core flows.

**Phase 4 (P3) — “Polish and long-term” (as capacity allows)**  
- P3-1: Onboarding doc.  
- P3-2: Threat ID consistency and CI check.  
- P3-3: Dashboard/API polish for demos.  
- Outcome: Easier onboarding; consistent taxonomy references; better demo UX.

**Dependencies:**  
- P0-1 unblocks believable multi-agent demos and any scenario that assumes orchestrator delegation.  
- P1-1 and P1-2 benefit from P0-1 (agent-driven scenarios that use Orchestrator).  
- P1-3 is independent but improves all scenario reporting.  
- P2-* can run in parallel after P1.

---

# One-Page Summary for CTO

| Priority | Item | One-line | Effort |
|----------|------|----------|--------|
| **P0** | Orchestrator reliability | Fix so Orchestrator reliably routes to Researcher/Executor via A2A; add deterministic path + E2E test. | 1–2 sprints |
| **P1** | Scenario–agent linkage | Add agent-driven scenarios (prompt → agent → assert state) per category. | 0.5–1 sprint |
| **P1** | Taxonomy coverage | Add scenarios: Rogue Agent Insertion, Replay, Coordinated multi-agent; document out-of-scope. | ~0.5 sprint |
| **P1** | Evidence schema | Standardize audit/evidence fields; ensure MCPs and scenarios use them. | ~0.5 sprint |
| **P2** | TUI or scope | Implement minimal TUI or document “Dashboard + API only.” | 0.25–1 sprint |
| **P2** | Keycloak/docs | Document expected Keycloak state and identity testing; add health check. | ~0.25 sprint |
| **P2** | Tests | E2E for orchestrator; scenario success tests in CI. | ~0.25–0.5 sprint |
| **P3** | Onboarding, threat ID, dashboard polish | Docs and UX polish. | ~0.5–1 sprint |

**Bottom line:** The lab is **architecturally complete** and **~79% taxonomy coverage**; the **main blocker** is **Orchestrator reliability (P0)**. Addressing P0 then P1 makes the lab CTO-ready for red team exercises and demos; P2 and P3 improve usability and maintainability.
