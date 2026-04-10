import { useEffect, useMemo, useState } from "react";

const RADIUS = 44;
const STROKE = 8;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const ScoreRing = ({ score = 0 }) => {
  const normalized = Math.max(0, Math.min(100, Number(score) || 0));
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setProgress(normalized));
    return () => cancelAnimationFrame(frame);
  }, [normalized]);

  const offset = useMemo(() => CIRCUMFERENCE - (progress / 100) * CIRCUMFERENCE, [progress]);

  return (
    <div className="relative h-28 w-28">
      <svg className="h-28 w-28 -rotate-90" viewBox="0 0 100 100" aria-label={`Health score ${normalized} out of 100`}>
        <circle cx="50" cy="50" r={RADIUS} fill="none" stroke="var(--border)" strokeWidth={STROKE} />
        <circle
          cx="50"
          cy="50"
          r={RADIUS}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 800ms cubic-bezier(0.4, 0, 0.2, 1)" }}
        />
      </svg>

      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-2xl font-bold text-text">{normalized}</span>
      </div>
    </div>
  );
};

export default ScoreRing;
