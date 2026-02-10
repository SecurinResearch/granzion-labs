import { useState, useEffect } from 'react';
import { FileSearch, RefreshCw, User, Activity, Clock } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getEvidence } from '../services/api';

interface EvidenceEntry {
    id: string;
    actor: { user_id?: string; agent_id?: string; identity_name?: string };
    action: string;
    resource?: string;
    timestamp?: string;
    identity_context?: Record<string, unknown>;
    details?: Record<string, unknown>;
}

export const EvidencePanel = () => {
    const [evidence, setEvidence] = useState<EvidenceEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchEvidence = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getEvidence(100);
            setEvidence(data.evidence || []);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load evidence');
            setEvidence([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEvidence();
        const interval = setInterval(fetchEvidence, 10000);
        return () => clearInterval(interval);
    }, []);

    const formatTime = (ts: string | undefined) => {
        if (!ts) return '—';
        try {
            const d = new Date(ts);
            return d.toLocaleTimeString('en-US', { hour12: false }) + ' ' + d.toLocaleDateString();
        } catch {
            return ts;
        }
    };

    return (
        <div className="space-y-6 h-full flex flex-col">
            <div className="flex items-center justify-between">
                <h3 className="text-2xl font-black text-white flex items-center gap-3">
                    <FileSearch className="text-primary" size={28} />
                    Red Team Evidence
                </h3>
                <button
                    onClick={fetchEvidence}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/20 hover:bg-primary/30 transition-all disabled:opacity-50 text-sm font-bold"
                >
                    <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                    Refresh
                </button>
            </div>

            <p className="text-sm text-gray-400">
                Audit log entries from MCP tool calls and agent actions (evidence schema). Use for red team reporting and scenario verification.
            </p>

            {loading && evidence.length === 0 ? (
                <div className="flex-1 flex items-center justify-center">
                    <div className="w-12 h-12 border-4 border-white/10 border-t-primary rounded-full animate-spin" />
                </div>
            ) : error ? (
                <div className="flex-1 flex items-center justify-center text-highlight">
                    {error}
                </div>
            ) : (
                <div className="flex-1 overflow-y-auto pr-4 custom-scrollbar space-y-3">
                    <AnimatePresence mode="popLayout">
                        {evidence.length === 0 ? (
                            <motion.p
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="text-gray-500 italic py-8 text-center"
                            >
                                No evidence recorded yet. Run scenarios or use the console to generate audit entries.
                            </motion.p>
                        ) : (
                            evidence.map((entry, i) => (
                                <motion.div
                                    key={entry.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0 }}
                                    className="glass-dark p-4 rounded-2xl border border-white/5 hover:border-primary/20 transition-colors"
                                >
                                    <div className="flex flex-wrap items-center gap-3 mb-2">
                                        <span className="flex items-center gap-1.5 text-primary font-mono text-sm">
                                            <Activity size={14} />
                                            {entry.action}
                                        </span>
                                        {entry.resource && (
                                            <span className="text-gray-400 text-xs font-mono truncate max-w-[200px]" title={entry.resource}>
                                                {entry.resource}
                                            </span>
                                        )}
                                        <span className="flex items-center gap-1 text-gray-500 text-xs ml-auto">
                                            <Clock size={12} />
                                            {formatTime(entry.timestamp)}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2 text-gray-400 text-sm">
                                        <User size={14} />
                                        <span>
                                            {entry.actor?.identity_name || entry.actor?.agent_id || entry.actor?.user_id || 'Unknown'}
                                        </span>
                                    </div>
                                </motion.div>
                            ))
                        )}
                    </AnimatePresence>
                </div>
            )}
        </div>
    );
};
