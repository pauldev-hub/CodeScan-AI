import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Shield, Sparkles, TerminalSquare } from "lucide-react";

import Button from "../components/Common/Button";
import ScrollReveal from "../components/Common/ScrollReveal";
import { useAuth } from "../hooks/useAuth";
import { APP_ROUTES } from "../utils/constants";

const LandingPage = () => {
  const { enterGuestMode, loading } = useAuth();
  const navigate = useNavigate();

  return (
    <main className="mx-auto w-[min(1880px,calc(100vw-24px))] px-3 pb-16 pt-6 md:px-4 md:pb-24 md:pt-10">
      <section className="codescan-editor-surface overflow-hidden">
        <div className="grid gap-0 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="px-5 py-8 md:px-8 md:py-12 xl:px-12 xl:py-16">
            <ScrollReveal>
            <p className="font-mono text-xs uppercase tracking-[0.24em] text-accent">Analyze. Understand. Secure.</p>
            <h1 className="mt-4 max-w-4xl text-5xl font-bold leading-[0.94] text-text md:text-7xl">
              Premium code review
              <br />
              for teams who ship fast.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-text2 md:text-lg">
              CodeScan AI turns static findings into a living editor workspace with guided fixes, plain-English explanations, and review-ready exports.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link to={APP_ROUTES.signup}>
                <Button size="lg">
                  Create Free Account
                  <ArrowRight size={16} />
                </Button>
              </Link>
              <Button
                variant="ghost"
                size="lg"
                isLoading={loading}
                onClick={async () => {
                  try {
                    await enterGuestMode();
                    navigate(APP_ROUTES.dashboard, { replace: true });
                  } catch {
                    // Preserve existing landing page state if guest session fails.
                  }
                }}
              >
                Continue as Guest
              </Button>
              <Link to={APP_ROUTES.scan}>
                <Button variant="ghost" size="lg">
                  Open Scan Workspace
                </Button>
              </Link>
            </div>
            </ScrollReveal>

            <ScrollReveal className="mt-10 grid gap-3 md:grid-cols-3" delay={120}>
            <div className="rounded-[22px] border border-border bg-bg3/70 p-4">
              <Shield size={18} className="text-accent" />
              <p className="mt-3 text-sm font-semibold text-text">Risk-aware summaries</p>
              <p className="mt-1 text-sm text-text2">Highlight the issues that deserve action first.</p>
            </div>
            <div className="rounded-[22px] border border-border bg-bg3/70 p-4">
              <TerminalSquare size={18} className="text-accent" />
              <p className="mt-3 text-sm font-semibold text-text">Editor-like scanning</p>
              <p className="mt-1 text-sm text-text2">Paste, upload, or review repositories inside one workspace.</p>
            </div>
            <div className="rounded-[22px] border border-border bg-bg3/70 p-4">
              <Sparkles size={18} className="text-accent" />
              <p className="mt-3 text-sm font-semibold text-text">Beginner-safe AI guidance</p>
              <p className="mt-1 text-sm text-text2">Explain impact, risk, and fixes without the jargon wall.</p>
            </div>
            </ScrollReveal>
          </div>

          <div className="border-l border-border bg-[linear-gradient(180deg,rgba(255,255,255,0.02),transparent)] p-5 md:p-8">
            <ScrollReveal className="h-full" delay={160}>
            <div className="flex items-center justify-between rounded-2xl border border-border bg-bg3/70 px-4 py-3">
              <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-text3">scan.workspace.tsx</span>
              <span className="rounded-full border border-border bg-bg2 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-accent">
                Live review
              </span>
            </div>

            <div className="mt-4 rounded-[24px] border border-border bg-[color:var(--panel-strong)] p-4 shadow-[0_24px_60px_rgba(0,0,0,0.28)]">
              <div className="flex items-center gap-2 border-b border-border pb-3">
                <span className="h-2.5 w-2.5 rounded-full bg-red/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-yellow/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-green/80" />
              </div>

              <div className="mt-4 grid grid-cols-[56px_1fr] overflow-hidden rounded-2xl border border-border">
                <div className="bg-[color:var(--editor-gutter)] px-3 py-4 font-mono text-xs leading-7 text-text3">
                  12
                  <br />
                  13
                  <br />
                  14
                  <br />
                  15
                  <br />
                  16
                </div>
                <div className="bg-bg2 px-4 py-4 font-mono text-[13px] leading-7 text-text">
                  <p>db.query(`SELECT * FROM users`)</p>
                  <p className="text-red">+ user controlled input</p>
                  <p className="text-text2">AI notes:</p>
                  <p className="text-accent">Use parameterized queries before shipping.</p>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl border border-border bg-bg3/60 p-4">
                  <p className="text-[11px] uppercase tracking-[0.16em] text-text3">Health score</p>
                  <p className="mt-3 text-4xl font-bold text-text">74</p>
                </div>
                <div className="rounded-2xl border border-border bg-bg3/60 p-4">
                  <p className="text-[11px] uppercase tracking-[0.16em] text-text3">AI assist</p>
                  <p className="mt-3 text-sm leading-6 text-text2">Explains the finding, the impact, and the safer implementation path.</p>
                </div>
              </div>
            </div>
            </ScrollReveal>
          </div>
        </div>
      </section>
    </main>
  );
};

export default LandingPage;
