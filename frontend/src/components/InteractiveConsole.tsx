import { useState, useRef, useEffect } from 'react';
import { Terminal, Send, Cpu, User, AlertCircle, Loader2, RotateCcw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../services/api';

interface Message {
    role: 'user' | 'agent';
    content: string;
    timestamp: Date;
}

export const InteractiveConsole = ({ agentId, agentName }: { agentId: string, agentName: string }) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [selectedIdentity, setSelectedIdentity] = useState('none');
    const scrollRef = useRef<HTMLDivElement>(null);

    const identities: any = {
        'none': { name: 'Anonymous', permissions: [], color: 'text-gray-500' },
        'alice': {
            name: 'Alice (User)',
            permissions: ['read', 'write'],
            color: 'text-blue-400',
            id: '00000000-0000-0000-0000-000000000001'
        },
        'bob': {
            name: 'Bob (Admin)',
            permissions: ['admin', 'delete', 'read', 'write'],
            color: 'text-red-400',
            id: '00000000-0000-0000-0000-000000000002'
        },
        'charlie': {
            name: 'Charlie (Restricted)',
            permissions: ['read'],
            color: 'text-green-400',
            id: '00000000-0000-0000-0000-000000000003'
        }
    };

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMsg: Message = { role: 'user', content: input, timestamp: new Date() };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const body: any = { prompt: input };

            if (selectedIdentity !== 'none') {
                const ident = identities[selectedIdentity];
                body.identity_context = {
                    user_id: ident.id,
                    permissions: ident.permissions,
                    created_at: new Date().toISOString()
                };
            }

            const response = await api.post(`/agents/${agentId}/run`, body);
            const agentMsg: Message = {
                role: 'agent',
                content: response.data.response,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, agentMsg]);
        } catch (err: any) {
            const errorMsg: Message = {
                role: 'agent',
                content: `Error: ${err.response?.data?.error || err.message}`,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full glass-dark rounded-3xl border border-white/10 overflow-hidden">
            {/* Console Header */}
            <div className="px-6 py-4 bg-white/5 border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary/20 rounded-lg text-primary">
                        <Terminal size={18} />
                    </div>
                    <div>
                        <h3 className="font-bold text-white text-sm">Interactive Red-Team Console</h3>
                        <p className="text-[10px] text-gray-500 uppercase tracking-widest font-mono">Target: {agentName}</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setMessages([])}
                        title="Clear chat (start fresh; agent does not remember past messages)"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-white/10 bg-white/5 text-gray-400 hover:text-white hover:border-white/20 transition-colors text-xs font-medium"
                    >
                        <RotateCcw size={12} />
                        Clear chat
                    </button>
                    <div className="flex items-center gap-2 bg-black/40 px-3 py-1.5 rounded-xl border border-white/5">
                        <span className="text-[10px] text-gray-400 uppercase font-bold">Identity:</span>
                        <select
                            value={selectedIdentity}
                            onChange={(e) => setSelectedIdentity(e.target.value)}
                            className={`bg-transparent text-xs font-mono focus:outline-none cursor-pointer ${identities[selectedIdentity].color}`}
                        >
                            {Object.entries(identities).map(([key, val]: [string, any]) => (
                                <option key={key} value={key} className="bg-[#0f172a] text-white">
                                    {val.name}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-success rounded-full animate-pulse" />
                        <span className="text-[10px] font-bold text-success uppercase">Uplink Active</span>
                    </div>
                </div>
            </div>

            {/* Messages Area */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar"
            >
                <AnimatePresence initial={false}>
                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-gray-600 space-y-4 opacity-50">
                            <Cpu size={48} />
                            <p className="font-mono text-sm">Direct neural link established. Awaiting command...</p>
                        </div>
                    ) : (
                        messages.map((msg, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div className={`max-w-[80%] flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-primary/20 text-primary' : 'bg-secondary/20 text-secondary'
                                        }`}>
                                        {msg.role === 'user' ? <User size={16} /> : <Cpu size={16} />}
                                    </div>
                                    <div className={`p-4 rounded-2xl text-sm leading-relaxed ${msg.role === 'user'
                                        ? 'bg-primary text-white rounded-tr-none'
                                        : 'bg-white/5 border border-white/10 text-gray-200 rounded-tl-none font-mono'
                                        }`}>
                                        {msg.content}
                                        <div className={`mt-2 text-[10px] opacity-50 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                                            {msg.timestamp.toLocaleTimeString()}
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        ))
                    )}
                    {loading && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex justify-start"
                        >
                            <div className="flex gap-3 items-center text-gray-500 font-mono text-xs italic p-4">
                                <Loader2 size={14} className="animate-spin" />
                                {agentName} is thinking...
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Input Area */}
            <div className="p-4 bg-black/40 border-t border-white/10">
                <div className="relative flex items-center gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSend()}
                        placeholder={`Instruct ${agentName}...`}
                        className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-primary/50 transition-all font-mono"
                    />
                    <button
                        onClick={handleSend}
                        disabled={loading || !input.trim()}
                        className="p-3 bg-primary text-white rounded-xl hover:bg-primary-dark transition-all disabled:opacity-50 disabled:grayscale"
                    >
                        <Send size={20} />
                    </button>
                </div>
                <div className="mt-2 flex flex-col gap-1 text-[10px] text-gray-500 px-1">
                    <div className="flex items-center gap-2">
                        <AlertCircle size={10} />
                        <span>Manual prompting bypasses orchestrator safety filters. Proceed with caution.</span>
                    </div>
                    <span className="opacity-80">Each message is sent alone; the agent does not see prior conversation. Use &quot;Clear chat&quot; to start a fresh thread in the UI.</span>
                </div>
            </div>
        </div>
    );
};
