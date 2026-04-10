import { useEffect, useMemo, useState } from "react";

const statusMessages = [
  "Warming up the secure workspace...",
  "Indexing your review surfaces...",
  "Preparing AI guidance layers...",
  "Opening the editor cockpit...",
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
      className={`fixed inset-0 z-50 flex items-center justify-center overflow-hidden bg-[radial-gradient(circle_at_16%_18%,rgba(214,161,108,0.24),transparent_28%),radial-gradient(circle_at_84%_18%,rgba(240,198,147,0.16),transparent_22%),radial-gradient(circle_at_50%_100%,rgba(255,255,255,0.06),transparent_30%),#120c0a] px-6 transition-opacity duration-500 ${
        isLeaving ? "opacity-0" : "opacity-100"
      }`}
      aria-live="polite"
    >
      <div className="absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(214,161,108,0.6),transparent)]" />
      <div className="pointer-events-none absolute left-[8%] top-[12%] hidden h-48 w-48 rounded-full bg-[rgba(214,161,108,0.12)] blur-3xl md:block" />
      <div className="pointer-events-none absolute bottom-[10%] right-[10%] hidden h-64 w-64 rounded-full bg-[rgba(240,198,147,0.08)] blur-3xl md:block" />

      <div className="w-full max-w-4xl rounded-[32px] border border-border bg-[color:var(--panel)] p-5 shadow-[0_30px_120px_rgba(0,0,0,0.46)] backdrop-blur-2xl md:p-8">
        <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.24em] text-accent">CodeScan AI Workspace</p>
            <h1 className="mt-4 max-w-xl text-4xl font-bold leading-[1.05] text-text md:text-6xl">
              Secure review,
              <br />
              editor-first.
            </h1>
            <p className="mt-4 max-w-lg text-sm text-text2 md:text-base">
              Launching the premium code review cockpit with guided findings, scan history, and AI-assisted fixes.
            </p>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-border bg-bg3/70 p-3">
                <p className="text-[10px] uppercase tracking-[0.18em] text-text3">Engine</p>
                <p className="mt-2 text-sm font-semibold text-text">Threat analysis</p>
              </div>
              <div className="rounded-2xl border border-border bg-bg3/70 p-3">
                <p className="text-[10px] uppercase tracking-[0.18em] text-text3">Context</p>
                <p className="mt-2 text-sm font-semibold text-text">Beginner-safe insights</p>
              </div>
              <div className="rounded-2xl border border-border bg-bg3/70 p-3">
                <p className="text-[10px] uppercase tracking-[0.18em] text-text3">Workspace</p>
                <p className="mt-2 text-sm font-semibold text-text">Editor-grade flow</p>
              </div>
            </div>
          </div>

          <div className="codescan-editor-surface min-h-[320px]">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-red/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-yellow/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-green/80" />
              </div>
              <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-text3">review.session</span>
            </div>

            <div className="p-4 md:p-5">
              <div className="rounded-2xl border border-border bg-[color:var(--editor-gutter)] p-4">
                <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.18em] text-text3">
                  <span>Boot sequence</span>
                  <span>{progress}%</span>
                </div>
                <div className="mt-4 h-[4px] overflow-hidden rounded-full bg-bg4">
                  <div
                    className="h-full rounded-full bg-[linear-gradient(90deg,var(--accent),var(--accent-2))] transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="mt-5 space-y-3 font-mono text-xs text-text2">
                  <p>init.workspace()</p>
                  <p>hydrate.scan.panels()</p>
                  <p className="text-accent">{status}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SplashScreen;
