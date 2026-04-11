import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
import { getSharedSummary } from "../services/summaryService";

const SharedSummaryPage = () => {
  const { shareUuid } = useParams();
  const [state, setState] = useState({ loading: true, payload: null, error: "" });

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const payload = await getSharedSummary(shareUuid);
        if (!cancelled) {
          setState({ loading: false, payload, error: "" });
        }
      } catch (error) {
        if (!cancelled) {
          setState({ loading: false, payload: null, error: error?.message || "Unable to load summary" });
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [shareUuid]);

  if (state.loading) {
    return <Card>Loading executive summary...</Card>;
  }

  if (state.error || !state.payload) {
    return <Card>{state.error || "Summary unavailable"}</Card>;
  }

  const summary = state.payload.executive_summary;

  return (
    <main className="mx-auto w-[min(1120px,calc(100vw-24px))] px-3 py-8 md:px-4 md:py-12">
      <div className="space-y-5">
        <ScrollReveal>
          <Card className="overflow-hidden bg-[linear-gradient(135deg,rgba(214,161,108,0.18),rgba(255,255,255,0.02))]">
            <p className="font-mono text-xs uppercase tracking-[0.24em] text-accent">Executive summary</p>
            <h1 className="mt-4 text-4xl font-bold text-text">{summary.headline}</h1>
            <p className="mt-3 text-sm leading-7 text-text2">{summary.plain_english}</p>
          </Card>
        </ScrollReveal>

        <div className="grid gap-5 md:grid-cols-3">
          <ScrollReveal delay={80}><Card><p className="text-[11px] uppercase tracking-[0.18em] text-text3">Verdict</p><p className="mt-3 text-2xl font-bold text-text">{summary.verdict}</p></Card></ScrollReveal>
          <ScrollReveal delay={120}><Card><p className="text-[11px] uppercase tracking-[0.18em] text-text3">Health score</p><p className="mt-3 text-2xl font-bold text-text">{state.payload.health_score}</p></Card></ScrollReveal>
          <ScrollReveal delay={160}><Card><p className="text-[11px] uppercase tracking-[0.18em] text-text3">Findings</p><p className="mt-3 text-2xl font-bold text-text">{state.payload.summary?.total_findings ?? 0}</p></Card></ScrollReveal>
        </div>

        <ScrollReveal delay={200}>
          <Card>
            <h2 className="text-lg font-bold text-text">Top risks</h2>
            <div className="mt-4 grid gap-3">
              {summary.top_risks?.map((risk) => (
                <div key={risk.title} className="rounded-2xl border border-border bg-bg3/70 p-4">
                  <p className="text-sm font-semibold text-text">{risk.title}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.14em] text-text3">{risk.severity}</p>
                  <p className="mt-2 text-sm text-text2">{risk.impact}</p>
                </div>
              ))}
            </div>
          </Card>
        </ScrollReveal>
      </div>
    </main>
  );
};

export default SharedSummaryPage;
