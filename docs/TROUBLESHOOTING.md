# Troubleshooting

## Console: agent responses feel unnatural / no memory

### Why responses feel stiff or procedural
The Orchestrator’s system prompt used to be very workflow-heavy (step-by-step, UUIDs, “do this in order”), so the model often echoed that style and narrated tool use (“I will call get_identity_context…”). We added a **Tone** section so it responds in a brief, natural way and doesn’t dump full workflows unless the user asks. If it still feels off, the model or temperature may need tuning.

### Does the agent remember past conversation?
**No.** Each request sends only the **current** user message. The backend does not receive or use conversation history, so the agent has no memory of earlier turns. The UI shows past messages for you only.

### How to “reset” for a new context
- **UI:** Use **Clear chat** in the Console header. This clears the visible thread only; the backend has no conversation state to clear.
- **A2A mailbox:** If you want the Orchestrator’s mailbox empty (e.g. after a scenario), that’s separate (Comms MCP stores messages in the DB). There is no single “reset all context” button; Clear chat is the reset for the **conversation** in the Console.

### Adding real conversation memory (future)
To have the agent remember past messages, the frontend would need to send a `messages` array (or `session_id` + history) to `POST /agents/{id}/run`, and the backend would need to pass that history into the agent (e.g. Agno’s chat API with message list). Not implemented today.

---

## PuppyGraph shows "not_reachable"

PuppyGraph is **optional**. The lab works without it (graph queries fall back to SQL). If you want the graph layer to be healthy, check the following.

### 1. PuppyGraph container is running

With Docker Compose:

```bash
docker compose ps
```

Ensure `granzion-puppygraph` (or the `puppygraph` service) is **Up**. If not:

```bash
docker compose up -d puppygraph
```

Wait a few seconds for the process inside the container to start (the Web UI may not respond immediately).

### 2. App runs inside Docker; PuppyGraph hostname

The app checks PuppyGraph at `http://{PUPPYGRAPH_HOST}:{port}`. Default host is **`puppygraph`** (the Compose service name). That hostname **only resolves when the app runs in the same Docker network** (e.g. the `granzion-lab` container). If you run the app **on the host** (e.g. `python -m src.main`), set:

```bash
# In .env or environment
PUPPYGRAPH_HOST=localhost
```

Then ensure PuppyGraph ports are exposed (Compose maps `8081:8081` and `8182:8182`), and the health check will try 8081.

### 3. 404 on ws://puppygraph:8081/gremlin (Invalid response status)
The **Gremlin** endpoint on the official PuppyGraph image is on port **8182**, not 8081. Port 8081 is the Web UI. Set `PUPPYGRAPH_PORT=8182` (e.g. in `.env` or docker-compose for the app). The app’s graph client uses `PUPPYGRAPH_PORT` for the WebSocket URL. Docker Compose should expose `8182:8182` for the PuppyGraph service.

### 4. Ports: Web UI 8081 vs 8082

The **official** PuppyGraph image uses:

- **8081** – Web UI (HTTP)
- **8182** – Gremlin (ws)

The lab’s health check tries the configured `PUPPYGRAPH_WEB_PORT`, then **8081**. If your image serves the Web UI on 8081, the check should succeed. If you use the official image and Gremlin, ensure the Gremlin port is **8182** and that Compose exposes it if the app connects from the host (e.g. `8182:8182`). The lab’s Gremlin client uses `PUPPYGRAPH_PORT` (default 8182 in config).

### 5. Summary

| Situation                         | Action |
|----------------------------------|--------|
| App in Docker, PuppyGraph in Compose | Start `puppygraph`: `docker compose up -d puppygraph`. Wait ~10s and refresh Dashboard. |
| App on host                      | Set `PUPPYGRAPH_HOST=localhost`. Ensure PuppyGraph container is running and ports 8081/8082 (and 8182 if using Gremlin) are mapped. |
| Don’t need graph                 | Ignore; backend uses SQL fallback and scenarios still run. |
