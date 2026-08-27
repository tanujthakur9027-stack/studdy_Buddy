"use client";
import { useRef, useCallback } from "react";

/**
 * useSound — Web Audio API sound effects for the quiz.
 *
 * All tones are synthesised on the fly (no audio files needed).
 * Returns a play(name) function that is safe to call server-side
 * (AudioContext only created on first call in the browser).
 */

type SoundName = "correct" | "wrong" | "tick" | "countdown" | "complete" | "select";

export function useSound() {
  const ctxRef = useRef<AudioContext | null>(null);

  const getCtx = useCallback((): AudioContext | null => {
    if (typeof window === "undefined") return null;
    if (!ctxRef.current) {
      try {
        ctxRef.current = new (window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      } catch {
        return null;
      }
    }
    return ctxRef.current;
  }, []);

  const play = useCallback(
    (name: SoundName) => {
      const ctx = getCtx();
      if (!ctx) return;

      // Resume if suspended (browser autoplay policy)
      if (ctx.state === "suspended") ctx.resume();

      const now = ctx.currentTime;

      switch (name) {
        case "select": {
          // Soft mid-tone click
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.frequency.value = 660;
          osc.type = "sine";
          gain.gain.setValueAtTime(0.12, now);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
          osc.start(now);
          osc.stop(now + 0.08);
          break;
        }

        case "correct": {
          // Rising two-note chime
          [523, 784].forEach((freq, i) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = freq;
            osc.type = "sine";
            const t = now + i * 0.12;
            gain.gain.setValueAtTime(0.0, t);
            gain.gain.linearRampToValueAtTime(0.22, t + 0.03);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.35);
            osc.start(t);
            osc.stop(t + 0.35);
          });
          break;
        }

        case "wrong": {
          // Descending buzz
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.type = "sawtooth";
          osc.frequency.setValueAtTime(220, now);
          osc.frequency.exponentialRampToValueAtTime(110, now + 0.25);
          gain.gain.setValueAtTime(0.18, now);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
          osc.start(now);
          osc.stop(now + 0.28);
          break;
        }

        case "tick": {
          // Quiet metronome click
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.frequency.value = 1000;
          osc.type = "square";
          gain.gain.setValueAtTime(0.06, now);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
          osc.start(now);
          osc.stop(now + 0.04);
          break;
        }

        case "countdown": {
          // Urgent high beep for last 5 seconds
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.frequency.value = 880;
          osc.type = "sine";
          gain.gain.setValueAtTime(0.15, now);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
          osc.start(now);
          osc.stop(now + 0.12);
          break;
        }

        case "complete": {
          // Victory arpeggio
          [523, 659, 784, 1047].forEach((freq, i) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = freq;
            osc.type = "sine";
            const t = now + i * 0.1;
            gain.gain.setValueAtTime(0.0, t);
            gain.gain.linearRampToValueAtTime(0.2, t + 0.04);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.5);
            osc.start(t);
            osc.stop(t + 0.5);
          });
          break;
        }
      }
    },
    [getCtx]
  );

  return { play };
}
