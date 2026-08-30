"use client";
import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Layers, Sparkles, RotateCcw,
  CheckCircle2, RefreshCw, Trophy, History, X,
} from "lucide-react";
import { api } from "@/lib/api";
import { Spinner, Badge, ProgressBar } from "@/components/ui";
import toast from "react-hot-toast";
import { clsx } from "clsx";

interface Props { docId?: string }

interface FlashCard { id: string; front: string; back: string; topic_tag: string }
interface Session { id: string; topic: string; created_at: string }

type Phase = "config" | "playing" | "summary";
type CardStatus = "pending" | "known" | "review";

const GRADE_META: Record<string, { label: string; color: string }> = {
  perfect:  { label: "Perfect! 🌟", color: "text-yellow-400" },
  great:    { label: "Great job! 🎉", color: "text-green-400" },
  good:     { label: "Good effort! 👍", color: "text-blue-400" },
  practice: { label: "Keep practising! 💪", color: "text-orange-400" },
};

function gradeFor(pct: number) {
  if (pct === 100) return "perfect";
  if (pct >= 75)  return "great";
  if (pct >= 50)  return "good";
  return "practice";
}

// ── Flip Card ────────────────────────────────────────────────────────────────
function FlipCard({ card, flipped, onFlip }: { card: FlashCard; flipped: boolean; onFlip: () => void }) {
  return (
    <div
      onClick={onFlip}
      className="relative cursor-pointer select-none"
      style={{ perspective: 1200, height: 240 }}
    >
      <motion.div
        animate={{ rotateY: flipped ? 180 : 0 }}
        transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
        style={{ transformStyle: "preserve-3d", position: "relative", width: "100%", height: "100%" }}
      >
        {/* Front */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center p-6 rounded-2xl bg-gray-900 border-2 border-gray-700 text-center"
          style={{ backfaceVisibility: "hidden" }}
        >
          {card.topic_tag && (
            <span className="text-[10px] text-brand-400 font-semibold uppercase tracking-widest mb-3">{card.topic_tag}</span>
          )}
          <p className="text-lg font-bold text-white leading-snug">{card.front}</p>
          <p className="text-xs text-gray-600 mt-4">Tap to reveal answer</p>
        </div>
        {/* Back */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center p-6 rounded-2xl bg-brand-600/10 border-2 border-brand-500/40 text-center"
          style={{ backfaceVisibility: "hidden", transform: "rotateY(180deg)" }}
        >
          {card.topic_tag && (
            <span className="text-[10px] text-brand-400 font-semibold uppercase tracking-widest mb-3">{card.topic_tag}</span>
          )}
          <p className="text-base text-gray-200 leading-relaxed">{card.back}</p>
        </div>
      </motion.div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function Flashcards({ docId }: Props) {
  const [phase,        setPhase]        = useState<Phase>("config");
  const [cards,        setCards]        = useState<FlashCard[]>([]);
  const [queue,        setQueue]        = useState<FlashCard[]>([]);
  const [statusMap,    setStatusMap]    = useState<Record<string, CardStatus>>({});
  const [currentIdx,   setCurrentIdx]   = useState(0);
  const [flipped,      setFlipped]      = useState(false);
  const [loading,      setLoading]      = useState(false);
  const [topic,        setTopic]        = useState("");
  const [sessions,     setSessions]     = useState<Session[]>([]);
  const [showHistory,  setShowHistory]  = useState(false);

  const loadSessions = useCallback(async () => {
    if (!docId) return;
    try {
      const res = await api.get(`/api/flashcards?doc_id=${docId}`);
      setSessions(res.data);
    } catch { /* non-critical */ }
  }, [docId]);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  const generate = async () => {
    if (!docId) { toast.error("Upload a document first!"); return; }
    setLoading(true);
    try {
      const res = await api.post("/api/flashcards/generate", { doc_id: docId, topic: topic.trim(), num_cards: 15 });
      const generated: FlashCard[] = res.data.cards;
      setCards(generated);
      startDeck(generated);
      loadSessions();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Generation failed";
      toast.error(msg);
    }
    setLoading(false);
  };

  const loadSession = async (sessionId: string) => {
    setLoading(true);
    try {
      const res = await api.get(`/api/flashcards/${sessionId}`);
      const loaded: FlashCard[] = res.data.cards;
      setCards(loaded);
      startDeck(loaded);
      setShowHistory(false);
    } catch {
      toast.error("Could not load deck");
    }
    setLoading(false);
  };

  const startDeck = (deck: FlashCard[]) => {
    const shuffled = [...deck].sort(() => Math.random() - 0.5);
    setQueue(shuffled);
    setStatusMap({});
    setCurrentIdx(0);
    setFlipped(false);
    setPhase("playing");
  };

  const handleKnow = () => {
    const card = queue[currentIdx];
    setStatusMap((prev) => ({ ...prev, [card.id]: "known" }));
    advance();
  };

  const handleReview = () => {
    const card = queue[currentIdx];
    setStatusMap((prev) => ({ ...prev, [card.id]: "review" }));
    // Re-append card to the end of queue
    setQueue((prev) => {
      const next = [...prev];
      next.push(next[currentIdx]);
      return next;
    });
    advance();
  };

  const advance = () => {
    setFlipped(false);
    const nextIdx = currentIdx + 1;
    // Count how many un-reviewed cards are left in queue from nextIdx onwards
    const remaining = queue.slice(nextIdx).filter((c) => statusMap[c.id] !== "known").length;
    if (nextIdx >= queue.length || remaining === 0) {
      setPhase("summary");
    } else {
      setCurrentIdx(nextIdx);
    }
  };

  const restart = () => startDeck(cards);

  // ── Config screen ────────────────────────────────────────────────────────────
  if (phase === "config") {
    return (
      <div className="space-y-6">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-2xl bg-amber-500/10 text-amber-400 shrink-0">
            <Layers className="h-7 w-7" />
          </div>
          <div className="flex-1">
            <h2 className="section-heading">Flashcards</h2>
            <p className="text-sm text-gray-400 mt-1">AI generates flip-cards from your notes. Mark each card as &quot;Know it&quot; or &quot;Review it&quot; — review cards come back until you nail them.</p>
          </div>
          {sessions.length > 0 && (
            <button onClick={() => setShowHistory((v) => !v)}
              className="p-2 rounded-xl bg-gray-900 border border-gray-700 text-gray-400 hover:text-gray-200 transition-colors shrink-0">
              <History className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Past decks */}
        <AnimatePresence>
          {showHistory && sessions.length > 0 && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
              <div className="glass-card p-4 space-y-2">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">Past Decks</p>
                {sessions.map((s) => (
                  <button key={s.id} onClick={() => loadSession(s.id)}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 border border-gray-700 text-sm text-gray-300 transition-colors">
                    <span className="truncate">{s.topic}</span>
                    <span className="text-xs text-gray-500 ml-2 shrink-0">{new Date(s.created_at).toLocaleDateString()}</span>
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="space-y-3">
          <input value={topic} onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && generate()}
            placeholder="Focus topic (optional) — e.g. Photosynthesis, Chapter 3…"
            className="input-field w-full" />
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={generate} disabled={loading || !docId}
            className="btn-primary w-full justify-center py-3">
            {loading ? <><Spinner size="sm" /> Generating cards…</> : <><Sparkles className="h-4 w-4" /> Generate Flashcards</>}
          </motion.button>
          {!docId && <p className="text-xs text-gray-600 text-center">Upload a document first to generate flashcards.</p>}
        </div>
      </div>
    );
  }

  // ── Summary screen ─────────────────────────────────────────────────────────
  if (phase === "summary") {
    const knownCount  = Object.values(statusMap).filter((s) => s === "known").length;
    const totalUnique = cards.length;
    const pct = totalUnique > 0 ? Math.round((knownCount / totalUnique) * 100) : 0;
    const gMeta = GRADE_META[gradeFor(pct)];

    return (
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
        <div className="glass-card p-8 text-center space-y-3">
          <Trophy className="h-10 w-10 text-yellow-400 mx-auto" />
          <p className={clsx("text-2xl font-black", gMeta.color)}>{gMeta.label}</p>
          <p className="text-gray-400 text-sm">{knownCount} / {totalUnique} cards mastered</p>
          <ProgressBar value={pct} className="max-w-xs mx-auto h-3" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          {cards.map((c) => (
            <div key={c.id} className={clsx(
              "flex items-center gap-2 px-3 py-2 rounded-xl border text-xs",
              statusMap[c.id] === "known"
                ? "bg-green-500/10 border-green-500/25 text-green-400"
                : "bg-orange-500/10 border-orange-500/25 text-orange-400",
            )}>
              {statusMap[c.id] === "known"
                ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                : <RefreshCw className="h-3.5 w-3.5 shrink-0" />}
              <span className="truncate">{c.front}</span>
            </div>
          ))}
        </div>
        <div className="flex gap-3">
          <button onClick={() => setPhase("config")} className="btn-secondary flex-1 justify-center">
            <RotateCcw className="h-4 w-4" /> New Deck
          </button>
          <button onClick={restart} className="btn-primary flex-1 justify-center">
            <Layers className="h-4 w-4" /> Restart Deck
          </button>
        </div>
      </motion.div>
    );
  }

  // ── Playing screen ─────────────────────────────────────────────────────────
  const card = queue[currentIdx];
  const knownSoFar = Object.values(statusMap).filter((s) => s === "known").length;
  const progress = (knownSoFar / cards.length) * 100;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => setPhase("config")} className="p-1.5 rounded-xl bg-gray-900 border border-gray-700 text-gray-500 hover:text-gray-300 transition-colors">
          <X className="h-4 w-4" />
        </button>
        <div className="flex-1 space-y-1">
          <ProgressBar value={progress} className="h-2" />
          <p className="text-xs text-gray-500">{knownSoFar} / {cards.length} mastered</p>
        </div>
        <Badge variant="blue">{card?.topic_tag || "Card"}</Badge>
      </div>

      {/* Card */}
      <AnimatePresence mode="wait">
        {card && (
          <motion.div key={card.id} initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 }} transition={{ duration: 0.2 }}>
            <FlipCard card={card} flipped={flipped} onFlip={() => setFlipped((v) => !v)} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Action buttons — only shown after flip */}
      <AnimatePresence>
        {flipped && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-2 gap-3">
            <button onClick={handleReview}
              className="flex items-center justify-center gap-2 py-3 rounded-2xl bg-orange-500/15 border border-orange-500/30 text-orange-400 font-semibold hover:bg-orange-500/25 transition-colors">
              <RefreshCw className="h-4 w-4" /> Review it ↩
            </button>
            <button onClick={handleKnow}
              className="flex items-center justify-center gap-2 py-3 rounded-2xl bg-green-500/15 border border-green-500/30 text-green-400 font-semibold hover:bg-green-500/25 transition-colors">
              <CheckCircle2 className="h-4 w-4" /> Know it ✓
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {!flipped && (
        <p className="text-center text-xs text-gray-600">Tap the card to reveal the answer, then mark yourself</p>
      )}
    </div>
  );
}
