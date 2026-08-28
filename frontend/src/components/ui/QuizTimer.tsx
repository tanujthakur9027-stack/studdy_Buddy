"use client";
import { motion } from "framer-motion";

interface QuizTimerProps {
  timeLeft: number;
  totalTime: number;
  onTick?: (_t: number) => void;
}

/**
 * SVG circular countdown ring.
 * - Green  → > 50 % time remaining
 * - Yellow → 20–50 %
 * - Red    → < 20 % (pulses)
 */
export function QuizTimer({ timeLeft, totalTime }: QuizTimerProps) {
  const R = 28; // ring radius
  const C = 2 * Math.PI * R;
  const pct = Math.max(0, timeLeft / totalTime);
  const dash = pct * C;

  const color =
    pct > 0.5 ? "#22c55e" : pct > 0.2 ? "#eab308" : "#ef4444";

  const numColor =
    pct > 0.5 ? "text-green-400" : pct > 0.2 ? "text-yellow-400" : "text-red-400";

  return (
    <motion.div
      animate={pct <= 0.2 && timeLeft > 0 ? { scale: [1, 1.08, 1] } : { scale: 1 }}
      transition={{ repeat: pct <= 0.2 && timeLeft > 0 ? Infinity : 0, duration: 0.6 }}
      className="relative flex items-center justify-center"
      style={{ width: 72, height: 72 }}
    >
      {/* Track ring */}
      <svg
        width={72}
        height={72}
        className="absolute inset-0 -rotate-90"
        viewBox="0 0 72 72"
      >
        <circle
          cx={36} cy={36} r={R}
          fill="none"
          stroke="#1f2937"
          strokeWidth={6}
        />
        <circle
          cx={36} cy={36} r={R}
          fill="none"
          stroke={color}
          strokeWidth={6}
          strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={C - dash}
          style={{ transition: "stroke-dashoffset 0.9s linear, stroke 0.3s" }}
        />
      </svg>
      {/* Number */}
      <span className={`relative text-lg font-black tabular-nums ${numColor}`}>
        {timeLeft}
      </span>
    </motion.div>
  );
}
