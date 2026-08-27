"use client";
import { motion } from "framer-motion";
import { clsx } from "clsx";

interface SpinnerProps { size?: "sm" | "md" | "lg"; className?: string }

export function Spinner({ size = "md", className }: SpinnerProps) {
  const dim = { sm: "h-4 w-4", md: "h-6 w-6", lg: "h-10 w-10" }[size];
  return (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
      className={clsx("rounded-full border-2 border-brand-500 border-t-transparent", dim, className)}
    />
  );
}

interface BadgeProps {
  children: React.ReactNode;
  variant?: "blue" | "green" | "yellow" | "red" | "purple" | "gray";
  className?: string;
}

const variantMap = {
  blue:   "bg-blue-500/15 text-blue-400 border border-blue-500/25",
  green:  "bg-green-500/15 text-green-400 border border-green-500/25",
  yellow: "bg-yellow-500/15 text-yellow-400 border border-yellow-500/25",
  red:    "bg-red-500/15 text-red-400 border border-red-500/25",
  purple: "bg-purple-500/15 text-purple-400 border border-purple-500/25",
  gray:   "bg-gray-700/50 text-gray-400 border border-gray-700",
};

export function Badge({ children, variant = "gray", className }: BadgeProps) {
  return (
    <span className={clsx("badge", variantMap[variant], className)}>
      {children}
    </span>
  );
}

interface ProgressBarProps { value: number; max?: number; className?: string; color?: string }

export function ProgressBar({ value, max = 100, className, color = "bg-brand-500" }: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className={clsx("h-2 rounded-full bg-gray-800 overflow-hidden", className)}>
      <motion.div
        className={clsx("h-full rounded-full", color)}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      />
    </div>
  );
}
