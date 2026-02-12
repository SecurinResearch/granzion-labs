import { useState, useEffect } from 'react';
import { Shield, CheckCircle, XCircle, Trash2, Key, Info, Lock, Loader2, RotateCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getAgentCard, rotateAgentKey } from '../services/api';

interface Props {
    agentId: string;
    agentName: string;
    onClose: () => void;
}

export const AgentCardDetail = ({ agentId, agentName, onClose }: Props) => {
    const [loading, setLoading] = useState(true);
    const [card, setCard] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [rotating, setRotating] = useState(false);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const fetchCard = async () => {
        try {
            const data = await getAgentCard(agentId);
            setCard(data);
        } catch (err) {
            setError('Failed to fetch Agent Card data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCard();
    }, [agentId]);

    const handleRotateKey = async () => {
        setRotating(true);
        setSuccessMessage(null);
        try {
            await rotateAgentKey(agentId);
            setSuccessMessage("Public key rotated successfully.");
            // Refresh card data
            await fetchCard();
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err) {
            console.error(err);
        } finally {
            setRotating(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
        >
            <div
                className="glass-dark w-full max-w-2xl rounded-3xl overflow-hidden shadow-2xl border border-white/10"
                onClick={e => e.stopPropagation()}
            >
                <div className="bg-gradient-to-r from-primary/20 to-secondary/20 p-8 border-b border-white/10 flex justify-between items-start">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <Shield className="text-primary" size={24} />
                            <span className="text-xs font-bold tracking-[0.2em] text-primary uppercase">Official Agno A2A Card</span>
                        </div>
                        <h2 className="text-3xl font-black text-white">{agentName}</h2>
                        <p className="text-gray-400 font-mono text-sm mt-1">{agentId}</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors">
                        <XCircle size={24} className="text-gray-500" />
                    </button>
                </div>

                <div className="p-8 space-y-8 max-h-[70vh] overflow-y-auto custom-scrollbar">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20 gap-4">
                            <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
                            <p className="text-gray-400 font-mono italic">Decrypting A2A Identity...</p>
                        </div>
                    ) : error ? (
                        <div className="bg-highlight/10 border border-highlight/20 p-6 rounded-2xl text-highlight flex items-center gap-4">
                            <XCircle size={32} />
                            <div>
                                <p className="font-bold">Protocol Error</p>
                                <p className="text-sm opacity-80">{error}</p>
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* Trust Status */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="glass p-4 rounded-2xl border-success/30">
                                    <p className="text-xs text-gray-500 uppercase font-bold mb-1">Verification</p>
                                    <div className="flex items-center gap-2 text-success font-bold">
                                        <CheckCircle size={18} />
                                        {card.is_verified ? 'VERIFIED' : 'UNVERIFIED'}
                                    </div>
                                </div>
                                <div className="glass p-4 rounded-2xl">
                                    <p className="text-xs text-gray-500 uppercase font-bold mb-1">Issuer ID</p>
                                    <p className="text-sm text-white font-mono truncate">{card.issuer_id || 'Self-Signed'}</p>
                                </div>
                            </div>

                            {/* Success Alert */}
                            <AnimatePresence>
                                {successMessage && (
                                    <motion.div
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                        className="bg-success/10 border border-success/20 p-4 rounded-xl text-success text-sm font-bold flex items-center gap-3"
                                    >
                                        <CheckCircle size={16} />
                                        {successMessage}
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Capabilities */}
                            <div>
                                <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                                    <Key size={16} className="text-accent" />
                                    Authorized Capabilities
                                </h4>
                                <div className="flex flex-wrap gap-2">
                                    {card.capabilities?.map((cap: string, i: number) => (
                                        <span key={i} className="px-3 py-1.5 bg-primary/10 border border-primary/20 text-primary rounded-lg text-sm font-medium">
                                            {cap}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            {/* Public Key */}
                            <div>
                                <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                                    <Lock size={16} className="text-warning" />
                                    Public Key (Ed25519)
                                </h4>
                                <div className="bg-black/40 p-4 rounded-2xl border border-white/5 font-mono text-xs text-gray-400 break-all leading-relaxed relative group">
                                    {card.public_key || 'No public key attached to this identity.'}
                                    {rotating && (
                                        <div className="absolute inset-0 bg-black/60 flex items-center justify-center rounded-2xl backdrop-blur-sm">
                                            <Loader2 size={24} className="text-primary animate-spin" />
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Advanced Metadata */}
                            {card.card_metadata && Object.keys(card.card_metadata).length > 0 && (
                                <div>
                                    <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                                        <Info size={16} className="text-secondary" />
                                        Extended Metadata
                                    </h4>
                                    <div className="grid grid-cols-2 gap-2">
                                        {Object.entries(card.card_metadata).map(([key, val]: [string, any], i) => (
                                            <div key={i} className="flex justify-between p-3 bg-white/5 rounded-xl border border-white/5">
                                                <span className="text-xs text-gray-500">{key}</span>
                                                <span className="text-xs text-white font-medium">{String(val)}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>

                <div className="p-6 bg-white/5 border-t border-white/5 flex gap-4">
                    <button
                        onClick={handleRotateKey}
                        disabled={rotating || loading}
                        className="flex-1 py-3 bg-primary text-white rounded-xl font-bold hover:bg-primary-dark transition-all shadow-lg hover:shadow-primary/20 flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                        {rotating ? <Loader2 size={18} className="animate-spin" /> : <RotateCw size={18} />}
                        {rotating ? 'ROTATING...' : 'Rotate Public Key'}
                    </button>
                    <button className="p-3 bg-highlight/10 text-highlight border border-highlight/20 rounded-xl hover:bg-highlight/20 transition-all group">
                        <Trash2 size={24} className="group-hover:scale-110 transition-transform" />
                    </button>
                </div>
            </div>
        </motion.div>
    );
};
