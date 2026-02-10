import { useState, useEffect, useRef } from 'react';
import { Play, Shield, Activity, ChevronRight, Loader2, CheckCircle, XCircle, FileText } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getScenarios, runScenario, getEvents } from '../services/api';

export interface ScenarioRunResult {
    scenario_id: string;
    status: string;
    success: boolean;
    message: string;
    duration_seconds?: number;
    steps_succeeded?: number;
    steps_failed?: number;
    steps_executed?: number;
    criteria_passed?: number;
    criteria_failed?: number;
    criteria_checked?: number;
    steps?: { description: string; status: string; error?: string }[];
    state_before?: Record<string, any>;
    state_after?: Record<string, any>;
    evidence?: string[];
    errors?: string[];
}

export const ScenarioPanel = () => {
    const [scenarios, setScenarios] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
    const [executing, setExecuting] = useState<string | null>(null);
    const [executionResult, setExecutionResult] = useState<ScenarioRunResult | null>(null);
    const [lastExecutedId, setLastExecutedId] = useState<string | null>(null);
    const [liveEvents, setLiveEvents] = useState<Array<{ timestamp: string; type: string; source: string; message: string }>>([]);
    const [eventFilter, setEventFilter] = useState<'ALL' | 'A2A' | 'SYSTEM'>('ALL');
    const livePollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    useEffect(() => {
        const fetchScenarios = async () => {
            try {
                const response = await getScenarios();
                setScenarios(response.scenarios || []);
            } catch (err) {
                console.error(err);
                setScenarios([]);
            } finally {
                setLoading(false);
            }
        };
        fetchScenarios();
    }, []);

    useEffect(() => {
        if (!executing) {
            if (livePollRef.current) {
                clearInterval(livePollRef.current);
                livePollRef.current = null;
            }
            setLiveEvents([]);
            return;
        }
        const poll = async () => {
            try {
                const data = await getEvents();
                if (data.events?.length) setLiveEvents(data.events.slice(0, 15));
            } catch {
                // ignore
            }
        };
        poll();
        livePollRef.current = setInterval(poll, 2000);
        return () => {
            if (livePollRef.current) clearInterval(livePollRef.current);
        };
    }, [executing]);

    const handleInitiate = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setExecuting(id);
        setExecutionResult(null);
        setLiveEvents([]);
        try {
            const res = await runScenario(id);
            setExecutionResult(res as ScenarioRunResult);
            setLastExecutedId(id);
        } catch (err: unknown) {
            const msg = err && typeof err === 'object' && 'message' in err ? String((err as Error).message) : 'Request failed';
            setExecutionResult({
                scenario_id: id,
                status: 'error',
                success: false,
                message: msg,
                errors: [msg],
            });
            setLastExecutedId(id);
        } finally {
            setExecuting(null);
        }
    };

    return (
        <div className="space-y-8 h-full flex flex-col">
            <div className="flex items-center justify-between">
                <h3 className="text-2xl font-black text-white flex items-center gap-3">
                    <Shield className="text-primary" size={28} />
                    Attack Scenario Hub
                </h3>
                <span className="px-4 py-1.5 bg-highlight/10 text-highlight border border-highlight/20 rounded-full text-xs font-bold uppercase tracking-widest">
                    Red Teaming Active
                </span>
            </div>

            {loading ? (
                <div className="flex-1 flex items-center justify-center">
                    <div className="w-12 h-12 border-4 border-white/10 border-t-primary rounded-full animate-spin" />
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 overflow-y-auto flex-1 pr-4 custom-scrollbar">
                    {scenarios.map((scenario) => (
                        <motion.div
                            key={scenario.id}
                            whileHover={{ scale: 1.01 }}
                            className={`glass-dark p-6 rounded-3xl border transition-all cursor-pointer ${selectedScenario === scenario.id ? 'border-primary ring-1 ring-primary/50 bg-primary/5' : 'border-white/5 hover:border-white/10'
                                }`}
                            onClick={() => setSelectedScenario(scenario.id)}
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-3 bg-white/5 rounded-2xl">
                                    <Activity size={24} className={scenario.threat_category?.startsWith('M') ? 'text-highlight' : 'text-primary'} />
                                </div>
                                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest px-2 py-1 bg-white/5 rounded-md border border-white/5">
                                    {scenario.threat_category || 'T-Unknown'}
                                </span>
                            </div>

                            <h4 className="text-lg font-bold text-white mb-2">{scenario.name}</h4>
                            <p className="text-sm text-gray-400 line-clamp-2 mb-6 h-10">{scenario.description}</p>

                            <div className="flex items-center justify-between mt-auto">
                                <div className="flex gap-1">
                                    {[1, 2, 3].map(i => (
                                        <div key={i} className={`w-1.5 h-1.5 rounded-full ${i <= (scenario.complexity || 2) ? 'bg-primary' : 'bg-white/10'}`} />
                                    ))}
                                </div>
                                <button
                                    onClick={(e) => handleInitiate(scenario.id, e)}
                                    disabled={executing === scenario.id}
                                    className={`flex items-center gap-2 group px-4 py-2 rounded-xl transition-all ${executing === scenario.id
                                        ? 'bg-success/20 text-success border-success/20'
                                        : 'bg-primary/20 text-primary border-primary/20 hover:bg-primary hover:text-white'
                                        } border`}
                                >
                                    {executing === scenario.id ? (
                                        <>
                                            <span className="text-xs font-bold">RUNNING</span>
                                            <Loader2 size={12} className="animate-spin" />
                                        </>
                                    ) : (
                                        <>
                                            <span className="text-xs font-bold">INITIATE</span>
                                            <Play size={12} fill="currentColor" />
                                        </>
                                    )}
                                </button>
                            </div>
                        </motion.div>
                    ))}
                </div>
            )}

            {/* Execution Trace Panel */}
            <AnimatePresence>
                {selectedScenario && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="h-64 glass-dark rounded-3xl border border-primary/20 p-8 flex flex-col justify-center items-center text-center gap-4 bg-gradient-to-t from-primary/5 to-transparent shadow-[0_-20px_40px_-15px_rgba(59,130,246,0.1)]"
                    >
                        {executing === selectedScenario ? (
                            <div className="flex flex-col gap-4 w-full h-full overflow-hidden">
                                <div className="flex flex-col items-center gap-2 shrink-0">
                                    <div className="w-16 h-16 bg-primary/20 rounded-full flex items-center justify-center text-primary border border-primary/20 animate-pulse">
                                        <Loader2 size={32} className="animate-spin" />
                                    </div>
                                    <p className="font-bold text-white text-lg">Attack in progress</p>
                                    <div className="flex gap-1 text-[10px] bg-black/20 p-0.5 rounded-lg border border-white/5">
                                        {(['ALL', 'A2A', 'SYSTEM'] as const).map(type => (
                                            <button
                                                key={type}
                                                onClick={() => setEventFilter(type)}
                                                className={`px-2 py-0.5 rounded-md transition-all ${eventFilter === type ? 'bg-primary/20 text-primary font-bold' : 'text-gray-500 hover:text-gray-300'}`}
                                            >
                                                {type}
                                            </button>
                                        ))}
                                    </div>
                                    <p className="text-gray-400 text-xs">Live activity (agent → MCP/tools)</p>
                                </div>
                                <div className="flex-1 min-h-0 overflow-y-auto font-mono text-xs space-y-1 pr-2 custom-scrollbar">
                                    {liveEvents.length === 0 ? (
                                        <p className="text-gray-500 italic">Polling for events...</p>
                                    ) : (
                                        liveEvents.filter(evt => {
                                            if (eventFilter === 'ALL') return true;
                                            if (eventFilter === 'A2A') return evt.type === 'A2A';
                                            if (eventFilter === 'SYSTEM') return evt.type !== 'A2A';
                                            return true;
                                        }).map((evt, i) => (
                                            <div key={i} className="flex gap-2 py-1 border-b border-white/5">
                                                <span className="text-blue-400 shrink-0">[{evt.timestamp}]</span>
                                                <span className="text-primary shrink-0">{evt.source}</span>
                                                <span className="text-gray-500 shrink-0">{evt.type}</span>
                                                <span className="text-gray-300 truncate">{evt.message}</span>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        ) : executionResult && selectedScenario === lastExecutedId ? (
                            <div className="flex flex-col gap-4 w-full h-full overflow-hidden text-left">
                                <div className="flex items-center gap-4 shrink-0">
                                    {executionResult.success ? (
                                        <div className="w-16 h-16 bg-success/20 rounded-full flex items-center justify-center text-success border border-success/20 shrink-0">
                                            <CheckCircle size={32} />
                                        </div>
                                    ) : (
                                        <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center text-red-400 border border-red-500/20 shrink-0">
                                            <XCircle size={32} />
                                        </div>
                                    )}
                                    <div>
                                        <p className="font-bold text-white text-lg">{executionResult.success ? 'Scenario passed' : 'Scenario failed'}</p>
                                        <p className="text-gray-400 text-sm">{executionResult.message}</p>
                                        {executionResult.duration_seconds != null && (
                                            <p className="text-gray-500 text-xs mt-1">Duration: {executionResult.duration_seconds.toFixed(1)}s</p>
                                        )}
                                    </div>
                                </div>

                                <div className="flex gap-2 text-xs mb-2">
                                    <div className="px-2 py-1 bg-white/5 rounded border border-white/5">
                                        <span className="text-gray-400">Steps:</span> <span className={executionResult.steps_failed ? "text-red-400" : "text-success"}>{executionResult.steps_succeeded ?? 0}/{executionResult.steps_executed}</span>
                                    </div>
                                    <div className="px-2 py-1 bg-white/5 rounded border border-white/5">
                                        <span className="text-gray-400">Criteria:</span> <span className={executionResult.criteria_failed ? "text-red-400" : "text-success"}>{executionResult.criteria_passed ?? 0}/{executionResult.criteria_checked}</span>
                                    </div>
                                </div>

                                {/* Steps Visualization */}
                                {executionResult.steps && executionResult.steps.length > 0 && (
                                    <div className="mb-4 w-full shrink-0">
                                        <p className="text-gray-400 text-xs font-medium mb-2 uppercase tracking-wider">Attack Steps</p>
                                        <div className="space-y-2 bg-black/20 rounded-lg p-3">
                                            {executionResult.steps.map((step, idx) => (
                                                <div key={idx} className="flex items-start gap-2 text-xs">
                                                    {step.status === 'completed' ? (
                                                        <CheckCircle size={14} className="text-success shrink-0 mt-0.5" />
                                                    ) : step.status === 'failed' ? (
                                                        <XCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
                                                    ) : (
                                                        <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-600 shrink-0 mt-0.5" />
                                                    )}
                                                    <div>
                                                        <p className={step.status === 'failed' ? 'text-red-300' : 'text-gray-300'}>{step.description}</p>
                                                        {step.error && <p className="text-red-400/70 text-[10px] mt-0.5">{step.error}</p>}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* State Comparison */}
                                {(executionResult.state_before || executionResult.state_after) && (
                                    <div className="mb-4 w-full flex-1 min-h-0 flex flex-col">
                                        <p className="text-gray-400 text-xs font-medium mb-2 uppercase tracking-wider">State Changes</p>
                                        <div className="flex-1 grid grid-cols-2 gap-2 min-h-0 bg-black/20 rounded-lg p-2 overflow-hidden">
                                            <div className="overflow-y-auto custom-scrollbar">
                                                <p className="text-[10px] text-gray-500 mb-1 sticky top-0 bg-black/80 px-1 py-0.5">BEFORE</p>
                                                <pre className="text-[10px] text-gray-400 font-mono whitespace-pre-wrap">
                                                    {JSON.stringify(executionResult.state_before, null, 2)}
                                                </pre>
                                            </div>
                                            <div className="overflow-y-auto custom-scrollbar border-l border-white/5 pl-2">
                                                <p className="text-[10px] text-gray-500 mb-1 sticky top-0 bg-black/80 px-1 py-0.5">AFTER</p>
                                                <pre className="text-[10px] text-gray-300 font-mono whitespace-pre-wrap">
                                                    {JSON.stringify(executionResult.state_after, null, 2)}
                                                </pre>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Evidence & Errors */}
                                {(executionResult.evidence?.length ?? 0) > 0 && (
                                    <div className="shrink-0 max-h-32 overflow-y-auto custom-scrollbar">
                                        <p className="text-gray-400 text-xs font-medium mb-1 flex items-center gap-1 uppercase tracking-wider">
                                            <FileText size={12} /> Evidence
                                        </p>
                                        <div className="bg-black/20 rounded-lg p-2 space-y-1">
                                            {executionResult.evidence!.map((ev, i) => (
                                                <div key={i} className="text-gray-300 text-xs truncate font-mono" title={str(ev)}>{typeof ev === 'string' ? ev : JSON.stringify(ev)}</div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <>
                                <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center text-primary border border-primary/20">
                                    <ChevronRight size={32} />
                                </div>
                                <div>
                                    <p className="font-bold text-white text-lg">Click INITIATE to begin execution</p>
                                    <p className="text-gray-400 text-sm max-w-sm mt-1 text-center">
                                        This will trigger the full agent-to-agent attack chain for "{scenarios.find(s => s.id === selectedScenario)?.name}".
                                    </p>
                                </div>
                            </>
                        )
                        }
                    </motion.div >
                )}
            </AnimatePresence >
        </div >
    );
};

// Helper to support string checking in render
const str = (val: any) => typeof val === 'string' ? val : JSON.stringify(val);
