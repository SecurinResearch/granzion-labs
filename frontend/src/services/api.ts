import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
});

export const getAgents = async () => {
    const response = await api.get('/agents');
    return response.data;
};

export const getAgentCard = async (agentId: string) => {
    const response = await axios.get(`/a2a/agents/${agentId}/.well-known/agent-card.json`);
    return response.data;
};

export const getScenarios = async () => {
    const response = await api.get('/scenarios');
    return response.data;
};

export const getSystemHealth = async () => {
    const response = await api.get('/health');
    return response.data;
};

/** Backend service statuses (postgres, pgvector, puppygraph, litellm, keycloak). Use for PuppyGraph Gremlin / vector DB checks. */
export const getServices = async () => {
    const response = await api.get('/services');
    return response.data;
};

export const getLogs = async () => {
    const response = await api.get('/logs');
    return response.data;
};

export const getEvents = async () => {
    const response = await api.get('/events');
    return response.data;
};

export const getEvidence = async (limit: number = 100) => {
    const response = await api.get('/evidence', { params: { limit } });
    return response.data;
};

/** Run a scenario via the engine; may take 1–2 min. Returns full result (success, steps, criteria, evidence). */
export const runScenario = async (scenarioId: string) => {
    const response = await api.post(`/scenarios/${scenarioId}/run`, {}, { timeout: 120000 });
    return response.data;
};

export const rotateAgentKey = async (agentId: string) => {
    const response = await api.post(`/agents/${agentId}/rotate-key`);
    return response.data;
};

export default api;
