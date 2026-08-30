"use client";
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Network, Sparkles, Printer, X, RotateCcw, Loader2, Download } from "lucide-react";
import { api } from "@/lib/api";
import toast from "react-hot-toast";

interface ConceptNode { id: string; label: string; type: string }
interface ConceptEdge { from_node: string; to_node: string; label: string }
interface ConceptMapData { nodes: ConceptNode[]; edges: ConceptEdge[] }

interface Props { docId: string; filename: string; onClose: () => void }

// ── Node layout (radial) ──────────────────────────────────────────────────────
function layoutNodes(nodes: ConceptNode[], W: number, H: number) {
  const cx = W / 2, cy = H / 2;
  const main   = nodes.filter((n) => n.type === "main");
  const sub    = nodes.filter((n) => n.type === "sub");
  const detail = nodes.filter((n) => n.type === "detail");

  const positions: Record<string, { x: number; y: number }> = {};

  // Main nodes — centre cluster
  main.forEach((n, i) => {
    const angle = (i / Math.max(main.length, 1)) * 2 * Math.PI;
    positions[n.id] = main.length === 1
      ? { x: cx, y: cy }
      : { x: cx + 70 * Math.cos(angle), y: cy + 50 * Math.sin(angle) };
  });

  // Sub nodes — middle ring
  sub.forEach((n, i) => {
    const angle = (i / sub.length) * 2 * Math.PI - Math.PI / 2;
    positions[n.id] = { x: cx + 180 * Math.cos(angle), y: cy + 140 * Math.sin(angle) };
  });

  // Detail nodes — outer ring
  detail.forEach((n, i) => {
    const angle = (i / Math.max(detail.length, 1)) * 2 * Math.PI - Math.PI / 4;
    positions[n.id] = { x: cx + 290 * Math.cos(angle), y: cy + 220 * Math.sin(angle) };
  });

  return positions;
}

const NODE_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  main:   { fill: "#1e3a5f", stroke: "#3b82f6", text: "#93c5fd" },
  sub:    { fill: "#1a2e1a", stroke: "#22c55e", text: "#86efac" },
  detail: { fill: "#2d1b2d", stroke: "#a855f7", text: "#d8b4fe" },
};

// ── SVG Concept Map ───────────────────────────────────────────────────────────
function ConceptMapSVG({ data }: { data: ConceptMapData }) {
  const W = 680, H = 500;
  const pos = layoutNodes(data.nodes, W, H);

  // Clamp positions to canvas
  const clamped: Record<string, { x: number; y: number }> = {};
  for (const [id, p] of Object.entries(pos)) {
    clamped[id] = { x: Math.max(70, Math.min(W - 70, p.x)), y: Math.max(36, Math.min(H - 36, p.y)) };
  }

  return (
    <svg
      id="concept-map-svg"
      viewBox={`0 0 ${W} ${H}`}
      className="w-full h-auto"
      xmlns="http://www.w3.org/2000/svg"
      style={{ background: "#0d1117" }}
    >
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="#4b5563" />
        </marker>
      </defs>

      {/* Edges */}
      {data.edges.map((e, i) => {
        const from = clamped[e.from_node];
        const to   = clamped[e.to_node];
        if (!from || !to) return null;
        const mx = (from.x + to.x) / 2;
        const my = (from.y + to.y) / 2;
        return (
          <g key={i}>
            <line
              x1={from.x} y1={from.y} x2={to.x} y2={to.y}
              stroke="#374151" strokeWidth="1.5"
              markerEnd="url(#arrow)"
            />
            <rect x={mx - 28} y={my - 9} width="56" height="16" rx="4" fill="#111827" fillOpacity="0.9" />
            <text x={mx} y={my + 4} textAnchor="middle" fontSize="9" fill="#6b7280" fontFamily="system-ui">
              {e.label}
            </text>
          </g>
        );
      })}

      {/* Nodes */}
      {data.nodes.map((n) => {
        const p = clamped[n.id];
        if (!p) return null;
        const colors = NODE_COLORS[n.type] ?? NODE_COLORS.detail;
        const words = n.label.split(" ");
        const line1 = words.slice(0, Math.ceil(words.length / 2)).join(" ");
        const line2 = words.slice(Math.ceil(words.length / 2)).join(" ");
        const rw = Math.max(60, n.label.length * 5.5);
        return (
          <g key={n.id}>
            <rect
              x={p.x - rw / 2} y={p.y - 18}
              width={rw} height={line2 ? 36 : 24}
              rx="8"
              fill={colors.fill}
              stroke={colors.stroke}
              strokeWidth="1.5"
            />
            <text x={p.x} y={p.y - (line2 ? 4 : 0)} textAnchor="middle" fontSize="11" fill={colors.text} fontWeight="600" fontFamily="system-ui">
              {line1}
            </text>
            {line2 && (
              <text x={p.x} y={p.y + 12} textAnchor="middle" fontSize="11" fill={colors.text} fontWeight="600" fontFamily="system-ui">
                {line2}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────
export function ConceptMapModal({ docId, filename, onClose }: Props) {
  const [topic,   setTopic]   = useState("");
  const [loading, setLoading] = useState(false);
  const [data,    setData]    = useState<ConceptMapData | null>(null);

  useEffect(() => { generate(""); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const generate = async (focusTopic: string) => {
    setLoading(true);
    setData(null);
    try {
      const res = await api.post("/api/concept-map", { doc_id: docId, topic: focusTopic });
      setData(res.data);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Generation failed";
      toast.error(msg);
    }
    setLoading(false);
  };

  const downloadSVG = () => {
    const svg = document.getElementById("concept-map-svg");
    if (!svg) return;
    const blob = new Blob([svg.outerHTML], { type: "image/svg+xml" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `concept-map-${filename.replace(/\.[^.]+$/, "")}.svg`;
    a.click();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 backdrop-blur-sm overflow-y-auto py-8 px-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96 }}
        className="w-full max-w-3xl bg-gray-950 border border-gray-800 rounded-2xl shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-center gap-3 p-5 border-b border-gray-800">
          <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 shrink-0">
            <Network className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-bold text-white">Concept Map</h2>
            <p className="text-xs text-gray-500 truncate mt-0.5">{filename}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {data && (
              <button onClick={downloadSVG} title="Download SVG"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gray-800 border border-gray-700 text-gray-300 hover:text-white text-xs font-medium transition-colors">
                <Download className="h-3.5 w-3.5" /> SVG
              </button>
            )}
            <button onClick={() => generate(topic)} disabled={loading} title="Regenerate"
              className="p-1.5 rounded-xl bg-gray-800 border border-gray-700 text-gray-400 hover:text-gray-200 transition-colors">
              <RotateCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button onClick={onClose} className="p-1.5 rounded-xl bg-gray-800 border border-gray-700 text-gray-400 hover:text-red-400 transition-colors">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Topic filter */}
        <div className="flex gap-2 p-4 border-b border-gray-800/60">
          <input value={topic} onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && generate(topic)}
            placeholder="Focus on a specific topic (optional)…"
            className="input-field flex-1 text-sm py-2" />
          <button onClick={() => generate(topic)} disabled={loading} className="btn-primary px-4 py-2 text-sm">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {loading ? "Generating…" : "Generate"}
          </button>
        </div>

        {/* Map area */}
        <div className="p-5 min-h-[300px] flex items-center justify-center">
          {loading && (
            <div className="flex items-center gap-3 text-gray-500">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm">Analysing document and building concept map…</span>
            </div>
          )}
          {data && !loading && <ConceptMapSVG data={data} />}
        </div>

        {/* Legend */}
        {data && (
          <div className="px-5 pb-4 flex items-center gap-5 text-[11px] text-gray-500">
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-blue-900 border border-blue-500 inline-block" />Main concept</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-green-900 border border-green-500 inline-block" />Sub-concept</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded bg-purple-900 border border-purple-500 inline-block" />Detail</span>
          </div>
        )}
      </motion.div>
    </div>
  );
}
