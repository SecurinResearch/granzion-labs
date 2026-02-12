import { useState, useEffect } from 'react';
import { Shield, ChevronDown, ChevronRight, AlertTriangle, ExternalLink, CheckCircle, Activity, Lock, Database, MessageSquare, Cpu, Eye, Settings, Bot } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getThreatMap } from '../services/api';

interface Threat {
    id: string;
    name: string;
    description: string;
    testable: boolean;
    scenario: string;
}

interface ThreatCategory {
    id: string;
    name: string;
    color: string;
    threats: Threat[];
}

const iconMap: Record<string, React.ReactNode> = {
    IT: <Lock size={20} />,
    M: <Database size={20} />,
    T: <Settings size={20} />,
    C: <MessageSquare size={20} />,
    O: <Bot size={20} />,
    A: <Cpu size={20} />,
    IF: <Activity size={20} />,
    V: <Eye size={20} />,
};

export const ThreatMapPanel = () => {
    const [categories, setCategories] = useState<ThreatCategory[]>([]);
    const [expandedCat, setExpandedCat] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [totalThreats, setTotalThreats] = useState(0);

    useEffect(() => {
        const fetch = async () => {
            try {
                const data = await getThreatMap();
                setCategories(data.categories || []);
                setTotalThreats(data.total_threats || 0);
            } catch { setCategories([]); }
            finally { setLoading(false); }
        };
        fetch();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="w-12 h-12 border-4 border-white/10 border-t-primary rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h3 className="text-2xl font-black text-white flex items-center gap-3">
                    <AlertTriangle className="text-red-500" size={28} />
                    Vulnerability Threat Map
                </h3>
                <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500">{totalThreats} threats across {categories.length} categories</span>
                    <span className="px-4 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full text-xs font-bold uppercase tracking-widest">
                        All Testable
                    </span>
                </div>
            </div>

            <p className="text-sm text-gray-400 max-w-2xl">
                Every vulnerability listed below is <strong className="text-white">intentionally planted</strong> in the lab and <strong className="text-white">testable via its linked scenario</strong>. Click a category to see individual threats, their descriptions, and which scenario exercises them.
            </p>

            {/* Category Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {categories.map((cat) => (
                    <motion.div
                        key={cat.id}
                        layout
                        className={`glass-dark rounded-2xl border transition-all cursor-pointer ${expandedCat === cat.id ? 'col-span-full border-opacity-50 ring-1 ring-opacity-30' : 'border-white/5 hover:border-white/15'
                            }`}
                        style={{ borderColor: expandedCat === cat.id ? cat.color : undefined, boxShadow: expandedCat === cat.id ? `0 0 20px ${cat.color}20` : undefined }}
                        onClick={() => setExpandedCat(expandedCat === cat.id ? null : cat.id)}
                    >
                        {/* Category Card */}
                        <div className="p-5">
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-3">
                                    <div className="p-2.5 rounded-xl" style={{ backgroundColor: `${cat.color}15`, color: cat.color }}>
                                        {iconMap[cat.id] || <Shield size={20} />}
                                    </div>
                                    <div>
                                        <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: cat.color }}>{cat.id}</p>
                                        <p className="text-sm font-bold text-white">{cat.name}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="px-2.5 py-1 rounded-lg text-xs font-bold" style={{ backgroundColor: `${cat.color}15`, color: cat.color }}>
                                        {cat.threats.length}
                                    </span>
                                    {expandedCat === cat.id ? <ChevronDown size={16} className="text-gray-500" /> : <ChevronRight size={16} className="text-gray-500" />}
                                </div>
                            </div>

                            {/* Threat ID pills when collapsed */}
                            {expandedCat !== cat.id && (
                                <div className="flex flex-wrap gap-1 mt-2">
                                    {cat.threats.map(t => (
                                        <span key={t.id} className="text-[9px] font-mono px-1.5 py-0.5 rounded"
                                            style={{ backgroundColor: `${cat.color}10`, color: `${cat.color}99` }}>
                                            {t.id}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Expanded Threats Table */}
                        <AnimatePresence>
                            {expandedCat === cat.id && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.25 }}
                                    className="overflow-hidden"
                                >
                                    <div className="px-5 pb-5 pt-1 border-t border-white/5 space-y-2">
                                        {cat.threats.map((threat, idx) => (
                                            <motion.div
                                                key={threat.id}
                                                initial={{ opacity: 0, x: -10 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: idx * 0.04 }}
                                                className="flex items-start gap-3 p-3 rounded-xl bg-black/20 border border-white/5 hover:border-white/10 transition-all"
                                            >
                                                <div className="shrink-0 mt-0.5">
                                                    <CheckCircle size={14} className="text-emerald-400" />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-start justify-between">
                                                        <div>
                                                            <span className="text-[10px] font-mono font-bold mr-2" style={{ color: cat.color }}>{threat.id}</span>
                                                            <span className="text-xs font-bold text-white">{threat.name}</span>
                                                        </div>
                                                        <span className="text-[10px] px-2 py-0.5 rounded-md bg-primary/10 text-primary font-mono shrink-0 ml-2">
                                                            {threat.scenario}
                                                        </span>
                                                    </div>
                                                    <p className="text-[11px] text-gray-400 mt-1">{threat.description}</p>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </motion.div>
                ))}
            </div>

            {/* Legend */}
            <div className="flex items-center gap-4 text-[10px] text-gray-500 pt-2 border-t border-white/5">
                <span className="flex items-center gap-1"><CheckCircle size={10} className="text-emerald-400" /> Testable in lab</span>
                <span className="flex items-center gap-1"><ExternalLink size={10} className="text-primary" /> Linked to scenario</span>
                <span>All vulnerabilities are real, intentionally planted code paths.</span>
            </div>
        </div>
    );
};
