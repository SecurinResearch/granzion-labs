import { useState, useEffect } from 'react';
import {
  Shield,
  Search,
  Terminal,
  Monitor,
  Activity,
  Cpu,
  Database,
  MessageSquare,
  Lock,
  Bell,
  User,
  FileSearch
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getAgents, getEvents, getLogs, getServices } from './services/api';
import { AgentCardDetail } from './components/AgentCardDetail';
import { ScenarioPanel } from './components/ScenarioPanel';
import { InteractiveConsole } from './components/InteractiveConsole';
import { EvidencePanel } from './components/EvidencePanel';

// --- Types ---
interface Agent {
  id: string;
  name: string;
  type: string;
  status: 'active' | 'idle' | 'warning';
  capabilities: string[];
  mcp_count: number;
}

// --- Components ---

const SidebarItem = ({ icon: Icon, label, active, onClick }: any) => (
  <button
    onClick={onClick}
    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 ${active
      ? 'bg-primary/20 text-primary border border-primary/30 shadow-[0_0_15px_rgba(59,130,246,0.2)]'
      : 'text-gray-400 hover:bg-white/5 hover:text-white'
      }`}
  >
    <Icon size={20} />
    <span className="font-medium">{label}</span>
  </button>
);

const AgentCard = ({ agent, onClick }: { agent: Agent, onClick: () => void }) => (
  <motion.div
    layout
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    whileHover={{ y: -5, scale: 1.02 }}
    className="glass-dark p-6 rounded-2xl relative overflow-hidden group"
  >
    <div className="absolute top-0 right-0 p-3 opacity-20 transition-opacity group-hover:opacity-100">
      <Shield size={40} className="text-primary" />
    </div>

    <div className="flex items-center gap-4 mb-4">
      <div className={`p-3 rounded-xl ${agent.status === 'active' ? 'bg-success/20 text-success' : 'bg-gray-500/20 text-gray-400'
        }`}>
        {agent.name === 'Orchestrator' && <Cpu size={24} />}
        {agent.name === 'Researcher' && <Search size={24} />}
        {agent.name === 'Executor' && <Terminal size={24} />}
        {agent.name === 'Monitor' && <Monitor size={24} />}
      </div>
      <div>
        <h3 className="text-xl font-bold text-white">{agent.name}</h3>
        <p className="text-sm text-gray-400 font-mono">{agent.id.slice(0, 8)}...</p>
      </div>
    </div>

    <div className="space-y-4">
      <div className="flex justify-between items-center text-sm">
        <span className="text-gray-400">Status</span>
        <span className={`flex items-center gap-2 ${agent.status === 'active' ? 'text-success' : 'text-gray-400'
          }`}>
          <span className={`w-2 h-2 rounded-full ${agent.status === 'active' ? 'bg-success animate-pulse' : 'bg-gray-500'
            }`} />
          {agent.status.toUpperCase()}
        </span>
      </div>

      <div className="flex justify-between items-center text-sm">
        <span className="text-gray-400">Capabilities</span>
        <span className="text-white font-medium">{agent.capabilities.length} Tools</span>
      </div>

      <div className="pt-4 border-t border-white/10 flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {agent.capabilities.slice(0, 3).map((cap, i) => (
          <span key={i} className="px-2 py-1 bg-white/5 rounded-md text-[10px] uppercase tracking-wider text-gray-300 border border-white/5 whitespace-nowrap">
            {cap}
          </span>
        ))}
        {agent.capabilities.length > 3 && (
          <span className="px-2 py-1 bg-white/5 rounded-md text-[10px] text-gray-400">
            +{agent.capabilities.length - 3}
          </span>
        )}
      </div>
    </div>

    <button
      onClick={onClick}
      className="mt-6 w-full py-2 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 hover:border-primary/40 rounded-xl text-sm font-semibold transition-all"
    >
      View Agent Card
    </button>
  </motion.div>
);

interface ServiceStatus {
  [key: string]: string;
}

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [services, setServices] = useState<ServiceStatus>({});
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [consoleAgentTarget, setConsoleAgentTarget] = useState<Agent | null>(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await getAgents();
        const agentList = response.agents || [];
        // Enrich data with capabilities for visualization
        const enrichedAgents = agentList.map((a: any) => ({
          ...a,
          status: 'active', // Default to active for live agents
          capabilities: a.permissions || ['mcp_tool', 'a2a_verify'],
          mcp_count: 5
        }));
        setAgents(enrichedAgents);
      } catch (error) {
        console.error("Failed to fetch agents:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchAgents();

    const fetchEvents = async () => {
      try {
        const data = await getEvents();
        if (data.events) {
          setEvents(prev => [...data.events, ...prev].slice(0, 50));
        }
      } catch (err) {
        console.error("Failed to fetch events:", err);
      }
    };

    const fetchLogs = async () => {
      try {
        const data = await getLogs();
        if (data.logs) {
          setLogs(data.logs);
        }
      } catch (err) {
        console.error("Failed to fetch logs:", err);
      }
    };

    fetchEvents();
    fetchLogs();
    getServices().then((d: { services?: ServiceStatus }) => d.services && setServices(d.services)).catch(() => {});

    // Polling every 5s for events, 10s for agents/logs, 15s for services
    const eventInterval = setInterval(fetchEvents, 5000);
    const mainInterval = setInterval(() => {
      fetchAgents();
      fetchLogs();
      getServices().then((d: { services?: ServiceStatus }) => d.services && setServices(d.services)).catch(() => {});
    }, 10000);

    return () => {
      clearInterval(eventInterval);
      clearInterval(mainInterval);
    };
  }, []);

  return (
    <div className="flex h-screen bg-[#030712] text-white overflow-hidden">
      {/* Sidebar */}
      <aside className="w-72 glass-dark m-4 mr-0 rounded-3xl flex flex-col p-6 gap-8 z-10 transition-all duration-500">
        <div className="flex items-center gap-3 px-2">
          <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(59,130,246,0.5)]">
            <Lock className="text-white" size={24} />
          </div>
          <h1 className="text-xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
            GRANZION LAB
          </h1>
        </div>

        <nav className="flex-1 space-y-2">
          <SidebarItem icon={Activity} label="Dashboard" active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} />
          <SidebarItem icon={Cpu} label="Agents" active={activeTab === 'agents'} onClick={() => setActiveTab('agents')} />
          <SidebarItem icon={Terminal} label="Console" active={activeTab === 'console'} onClick={() => setActiveTab('console')} />
          <SidebarItem icon={Shield} label="Scenarios" active={activeTab === 'scenarios'} onClick={() => setActiveTab('scenarios')} />
          <SidebarItem icon={FileSearch} label="Evidence" active={activeTab === 'evidence'} onClick={() => setActiveTab('evidence')} />
          <SidebarItem icon={MessageSquare} label="Live Traffic" active={activeTab === 'traffic'} onClick={() => setActiveTab('traffic')} />
          <SidebarItem icon={Database} label="System Logs" active={activeTab === 'logs'} onClick={() => setActiveTab('logs')} />
        </nav>

        <div className="p-4 bg-white/5 rounded-2xl border border-white/5 space-y-3">
          <div className="flex items-center justify-between text-xs text-gray-500 uppercase font-bold tracking-widest">
            <span>Status</span>
            <span className="text-success flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-success rounded-full" />
              Operational
            </span>
          </div>
          <div className="h-1 bg-white/5 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: '100%' }}
              transition={{ duration: 2 }}
              className="h-full bg-gradient-to-r from-primary to-secondary"
            />
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {/* Background Effects */}
        <div className="absolute top-0 left-0 w-full h-full bg-vignette pointer-events-none" />
        <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-secondary/10 rounded-full blur-[120px] pointer-events-none" />

        {/* Top Bar */}
        <header className="h-20 flex items-center justify-between px-10 relative z-10 border-b border-white/5 backdrop-blur-md">
          <div className="flex items-center gap-4">
            <h2 className="text-2xl font-bold capitalize">{activeTab}</h2>
            <div className="h-6 w-[1px] bg-white/10" />
            <p className="text-sm text-gray-400">Granzion System // Node-04</p>
          </div>

          <div className="flex items-center gap-6">
            <button className="text-gray-400 hover:text-white transition-colors relative">
              <Bell size={20} />
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-highlight rounded-full" />
            </button>
            <div className="flex items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/5">
              <div className="w-8 h-8 bg-gradient-to-tr from-primary to-secondary rounded-lg flex items-center justify-center">
                <User size={18} />
              </div>
              <span className="text-sm font-medium">Admin User</span>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-10 relative z-10 custom-scrollbar">
          <AnimatePresence mode="wait">
            {activeTab === 'dashboard' && (
              <motion.div
                key="dashboard"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-10"
              >
                {/* Stats Grid */}
                <div className="grid grid-cols-4 gap-6">
                  {[
                    { label: 'Total Agents', value: agents.length, icon: Cpu, color: 'text-primary' },
                    { label: 'Active Tasks', value: 12, icon: Activity, color: 'text-success' },
                    { label: 'Security Threats', value: 3, icon: Shield, color: 'text-highlight' },
                    { label: 'System Uptime', value: '99.9%', icon: Database, color: 'text-accent' },
                  ].map((stat, i) => (
                    <div key={i} className="glass p-6 rounded-2xl flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-400 mb-1">{stat.label}</p>
                        <p className="text-3xl font-black">{stat.value}</p>
                      </div>
                      <stat.icon className={stat.color} size={32} />
                    </div>
                  ))}
                </div>

                {/* Backend services: pgvector (vector DB) & PuppyGraph (Gremlin) */}
                <div className="glass p-6 rounded-2xl">
                  <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <Database size={20} />
                    Backend services (vector DB &amp; graph)
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
                    {[
                      { key: 'postgres', label: 'PostgreSQL' },
                      { key: 'pgvector', label: 'pgvector (vector DB)' },
                      { key: 'puppygraph', label: 'PuppyGraph (Gremlin)' },
                      { key: 'litellm', label: 'LiteLLM' },
                      { key: 'keycloak', label: 'Keycloak' },
                    ].map(({ key, label }) => {
                      const status = services[key];
                      const ok = status === 'healthy';
                      const warn = status && !ok && (status === 'missing' || status === 'not_reachable' || status.startsWith('not_'));
                      return (
                        <div
                          key={key}
                          className={`p-3 rounded-xl border text-sm ${ok ? 'bg-success/10 border-success/30 text-success' : warn ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' : 'bg-white/5 border-white/10 text-gray-400'}`}
                        >
                          <div className="font-medium truncate" title={label}>{label}</div>
                          <div className="text-xs mt-1 truncate" title={status || 'unknown'}>
                            {status || '—'}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-xs text-gray-500 mt-3">
                    Vector DB: pgvector powers agent memory (embeddings). PuppyGraph (Gremlin) powers graph queries over identities/delegation; if not reachable, backend uses SQL fallback.
                  </p>
                </div>

                {/* Agents Section */}
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-xl font-bold flex items-center gap-2">
                      <Cpu className="text-primary" size={24} />
                      Agent Cluster
                    </h3>
                    <button className="text-sm text-primary hover:underline font-semibold">Manage All</button>
                  </div>

                  {loading ? (
                    <div className="grid grid-cols-4 gap-6 animate-pulse">
                      {[1, 2, 3, 4].map(i => <div key={i} className="h-64 bg-white/5 rounded-2xl" />)}
                    </div>
                  ) : (
                    <div className="grid grid-cols-4 gap-6">
                      {agents.map(agent => <AgentCard key={agent.id} agent={agent} onClick={() => setSelectedAgent(agent)} />)}
                    </div>
                  )}
                </div>

                {/* Recent Activity */}
                <div className="glass-dark p-8 rounded-3xl border border-white/5">
                  <h3 className="text-xl font-bold mb-6">Live System Activity</h3>
                  <div className="space-y-4 font-mono text-sm max-h-64 overflow-y-auto pr-2 custom-scrollbar">
                    {events.length === 0 ? (
                      <p className="text-gray-500 italic">No recent activity detected. Lab is idle.</p>
                    ) : (
                      events.map((evt, i) => (
                        <div key={i} className={`flex gap-4 p-3 bg-white/5 rounded-lg border border-white/5 ${evt.type === 'ALERT' ? 'text-highlight' :
                          evt.type === 'INFO' ? 'text-success' :
                            evt.type === 'DELEGATE' ? 'text-primary' : 'text-accent'
                          }`}>
                          <span className="text-gray-500">[{evt.timestamp}]</span>
                          <span className="font-bold">{evt.type}</span>
                          <span className="text-gray-300 font-bold">{evt.source}</span>
                          <span>{evt.message}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'scenarios' && (
              <motion.div
                key="scenarios"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="h-full"
              >
                <ScenarioPanel />
              </motion.div>
            )}

            {activeTab === 'evidence' && (
              <motion.div
                key="evidence"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="h-full"
              >
                <EvidencePanel />
              </motion.div>
            )}

            {activeTab === 'agents' && (
              <motion.div
                key="agents"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
              >
                {agents.map(agent => (
                  <div key={agent.id} className="space-y-4">
                    <AgentCard agent={agent} onClick={() => setSelectedAgent(agent)} />
                    <button
                      onClick={() => {
                        setConsoleAgentTarget(agent);
                        setActiveTab('console');
                      }}
                      className="w-full py-2 bg-secondary/10 hover:bg-secondary/20 text-secondary border border-secondary/20 rounded-xl text-xs font-bold transition-all"
                    >
                      OPEN CONSOLE
                    </button>
                  </div>
                ))}
              </motion.div>
            )}

            {activeTab === 'console' && (
              <motion.div
                key="console"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="h-full"
              >
                {consoleAgentTarget ? (
                  <InteractiveConsole agentId={consoleAgentTarget.id} agentName={consoleAgentTarget.name} />
                ) : (
                  <div className="h-full flex flex-col items-center justify-center opacity-30 gap-4">
                    <Terminal size={64} />
                    <p className="text-xl font-mono">Select an agent from the Agents tab to initialize console link...</p>
                  </div>
                )}
              </motion.div>
            )}

            {activeTab === 'traffic' && (
              <motion.div
                key="traffic"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="h-full flex flex-col gap-6"
              >
                <div className="flex justify-between items-center">
                  <h3 className="text-2xl font-bold">A2A Message Live Stream</h3>
                  <div className="flex gap-2">
                    <span className="px-3 py-1 bg-success/20 text-success rounded-full text-xs font-bold">REALTIME</span>
                  </div>
                </div>
                <div className="flex-1 glass-dark rounded-3xl p-6 overflow-y-auto custom-scrollbar border border-white/5 font-mono text-sm space-y-2">
                  {events.map((evt, i) => (
                    <div key={i} className="flex gap-4 items-start border-b border-white/5 pb-2">
                      <span className="text-blue-400">[{evt.timestamp}]</span>
                      <span className="text-primary w-24 shrink-0">{evt.source}</span>
                      <span className="text-gray-400">→</span>
                      <div className="flex-1">
                        <span className={`px-2 py-0.5 rounded text-[10px] mr-3 font-bold ${evt.type === 'ALERT' ? 'bg-highlight/20 text-highlight' : 'bg-success/20 text-success'}`}>{evt.type}</span>
                        <span className="text-gray-200">{evt.message}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {activeTab === 'logs' && (
              <motion.div
                key="logs"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="h-full flex flex-col gap-6"
              >
                <div className="flex justify-between items-center">
                  <h3 className="text-2xl font-bold">System Log Explorer</h3>
                  <button
                    onClick={() => setLogs([])}
                    className="text-xs text-gray-500 hover:text-white transition-colors"
                  >
                    Clear View
                  </button>
                </div>
                <div className="flex-1 bg-black/60 rounded-3xl p-8 overflow-y-auto custom-scrollbar border border-white/10 font-mono text-xs leading-relaxed">
                  {logs.map((log, i) => (
                    <div key={i} className="py-0.5 whitespace-pre-wrap">
                      <span className="text-gray-600 mr-4">{(i + 1).toString().padStart(3, '0')}</span>
                      <span className={log.includes('ERROR') ? 'text-highlight' : log.includes('WARNING') ? 'text-yellow-500' : 'text-gray-400'}>
                        {log}
                      </span>
                    </div>
                  ))}
                  <div className="h-4" /> {/* Spacer for bottom */}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Overlays */}
      <AnimatePresence>
        {selectedAgent && (
          <AgentCardDetail
            agentId={selectedAgent.id}
            agentName={selectedAgent.name}
            onClose={() => setSelectedAgent(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

export default App;
