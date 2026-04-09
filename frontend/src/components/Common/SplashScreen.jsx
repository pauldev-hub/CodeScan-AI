import { useEffect, useMemo, useState } from "react";

const statusMessages = [
  "Loading secure analysis engine...",
  "Preparing scan insights...",
  "Syncing threat models...",
  "Almost ready...",
];

const SplashScreen = ({ onDone }) => {
  const [progress, setProgress] = useState(0);
  const [stepIndex, setStepIndex] = useState(0);
  const [isLeaving, setIsLeaving] = useState(false);

  useEffect(() => {
    const progressInterval = setInterval(() => {
      setProgress((value) => Math.min(100, value + 2));
    }, 55);

    const statusInterval = setInterval(() => {
      setStepIndex((index) => (index + 1) % statusMessages.length);
    }, 450);

    const leaveTimer = setTimeout(() => {
      setIsLeaving(true);
      setTimeout(() => onDone?.(), 420);
    }, 2600);

    return () => {
      clearInterval(progressInterval);
      clearInterval(statusInterval);
      clearTimeout(leaveTimer);
    };
  }, [onDone]);

  const status = useMemo(() => statusMessages[stepIndex], [stepIndex]);

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-[radial-gradient(circle_at_20%_20%,rgba(88,166,255,0.22),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(124,58,237,0.18),transparent_40%),var(--bg)] px-6 transition-opacity duration-400 ${
        isLeaving ? "opacity-0" : "opacity-100"
      }`}
      aria-live="polite"
    >
      <div className="w-full max-w-lg rounded-2xl border border-border bg-bg2/90 p-6 backdrop-blur">
        <p className="font-mono text-xs uppercase tracking-[0.14em] text-accent">CodeScan AI</p>
        <h1 className="mt-3 text-3xl font-bold text-text">Analyze. Understand. Secure.</h1>
        <p className="mt-2 text-sm text-text2">Security insights in plain English for every commit.</p>

        <div className="mt-6 h-[3px] w-full overflow-hidden rounded-full bg-bg3">
          <div className="h-full bg-accent transition-all duration-300" style={{ width: `${progress}%` }} />
        </div>

        <p className="mt-3 text-xs text-text2">{status}</p>
      </div>
    </div>
  );
};

export default SplashScreen;
