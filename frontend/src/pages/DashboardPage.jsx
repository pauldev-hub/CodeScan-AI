import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, ArrowRight, MessageSquare, Share2, Sparkles, Trophy } from "lucide-react";

import Button from "../components/Common/Button";
import Badge from "../components/Common/Badge";
import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
import ScanComparison from "../components/History/ScanComparison";
import ScoreTimeline from "../components/History/ScoreTimeline";
import { generateShareCard } from "../services/reportService";
import { getScanHistory } from "../services/scanService";
import { APP_ROUTES } from "../utils/constants";

const DashboardPage = () => {
  const [historyState, setHistoryState] = useState({ loading: true, items: [], page: 1, pages: 1, error: "" });
  const [shareState, setShareState] = useState({ loading: false, data: null, error: "" });

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setHistoryState((prev) => ({ ...prev, loading: true, error: "" }));
      try {
        const payload = await getScanHistory(historyState.page, 8);
        if (!cancelled) {
          setHistoryState((prev) => ({ ...prev, loading: false, items: payload.items || [], pages: payload.pages || 1, page: payload.page || prev.page }));
        }
      } catch (error) {
        if (!cancelled) {
          setHistoryState((prev) => ({ ...prev, loading: false, error: error?.message || "Unable to load scan history" }));
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [historyState.page]);

  const latest = historyState.items[0];
  const latestCompleted = useMemo(
    () => historyState.items.find((item) => item.status === "complete" && item.health_score !== null && item.health_score !== undefined) || null,
    [historyState.items]
  );
  const metrics = useMemo(() => {
    const items = historyState.items || [];
    const completed = items.filter((item) => item.status === "complete");
    const streak = completed.length ? Math.min(9, completed.length) : 0;
    return {
      streak,
      xp: completed.reduce((total, item) => total + Math.max(10, 100 - Number(item.health_score ?? 0)), 0),
      bestScore: completed.reduce((best, item) => Math.max(best, Number(item.health_score ?? 0)), 0),
    };
  }, [historyState.items]);

  const onGenerateShareCard = async () => {
    if (!latestCompleted?.scan_id) {
      return;
    }
    setShareState({ loading: true, data: null, error: "" });
    try {
      const payload = await generateShareCard(latestCompleted.scan_id);
      setShareState({ loading: false, data: payload, error: "" });
    } catch (error) {
      setShareState({ loading: false, data: null, error: error?.message || "Unable to generate share card copy" });
    }
  };

  return (
    <main className="space-y-5">
      <ScrollReveal className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="overflow-hidden">
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-accent">Command center</p>
          <h1 className="mt-4 text-4xl font-bold leading-tight text-text md:text-5xl">Track score movement, build streaks, and jump back into fixes fast.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-text2">The dashboard now surfaces momentum, share-ready summaries, and where your next fixes will make the biggest difference.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to={APP_ROUTES.scan}><Button>Start new scan<ArrowRight size={16} /></Button></Link>
            {latest ? <Link to={APP_ROUTES.results.replace(":scanId", latest.scan_id)}><Button variant="ghost">Open latest results</Button></Link> : null}
            <Link to={APP_ROUTES.chat}><Button variant="ghost"><MessageSquare size={16} />Open DevChat</Button></Link>
          </div>
        </Card>
        <Card className="bg-[linear-gradient(135deg,rgba(214,161,108,0.18),rgba(255,255,255,0.02))]">
          <div className="flex items-center gap-2 text-accent"><Sparkles size={16} /><span className="text-[11px] uppercase tracking-[0.18em]">Share card</span></div>
          <p className="mt-4 text-3xl font-bold text-text">{latestCompleted?.health_score ?? "n/a"}</p>
          <p className="mt-2 text-sm text-text2">Latest completed scan is used for a stakeholder-friendly summary instead of empty in-progress data.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button size="sm" onClick={onGenerateShareCard} isLoading={shareState.loading} disabled={!latestCompleted}>
              <Sparkles size={14} />
              Generate with AI
            </Button>
            {latestCompleted ? <Link to={APP_ROUTES.results.replace(":scanId", latestCompleted.scan_id)}><Button size="sm" variant="ghost">Open source scan</Button></Link> : null}
          </div>
          {shareState.data ? <p className="mt-3 text-sm leading-7 text-text2">{shareState.data.ai_copy}</p> : null}
          {shareState.error ? <p className="mt-3 text-sm text-red">{shareState.error}</p> : null}
        </Card>
      </ScrollReveal>

      <div className="grid gap-5 md:grid-cols-3">
        <ScrollReveal delay={70}><Card><div className="flex items-center gap-2 text-accent"><Trophy size={16} /><span className="text-[11px] uppercase tracking-[0.18em]">Fix streak</span></div><p className="mt-4 text-4xl font-bold text-text">{metrics.streak}</p><p className="mt-1 text-sm text-text2">Consecutive completed scans</p></Card></ScrollReveal>
        <ScrollReveal delay={110}><Card><div className="flex items-center gap-2 text-accent"><Activity size={16} /><span className="text-[11px] uppercase tracking-[0.18em]">XP</span></div><p className="mt-4 text-4xl font-bold text-text">{metrics.xp}</p><p className="mt-1 text-sm text-text2">Progress points from analyzed issues</p></Card></ScrollReveal>
        <ScrollReveal delay={150}><Card><div className="flex items-center gap-2 text-accent"><Share2 size={16} /><span className="text-[11px] uppercase tracking-[0.18em]">Best score</span></div><p className="mt-4 text-4xl font-bold text-text">{metrics.bestScore}</p><p className="mt-1 text-sm text-text2">Highest recorded health score</p></Card></ScrollReveal>
      </div>

      {historyState.loading ? <Card>Loading recent scans...</Card> : null}
      {historyState.error ? <Card>{historyState.error}</Card> : null}

      {!historyState.loading && !historyState.error && historyState.items.length ? (
        <>
          <ScrollReveal delay={180}>
            <Card>
              <div className="flex items-center justify-between gap-3">
                <div><h2 className="text-lg font-bold text-text">Health score timeline</h2><p className="mt-1 text-sm text-text2">Detailed trend with findings context instead of a bare line.</p></div>
                <Badge severity={(latest?.health_score ?? 0) > 79 ? "low" : "medium"}>{latest?.health_score ?? "n/a"}/100</Badge>
              </div>
              <div className="mt-4"><ScoreTimeline items={historyState.items} /></div>
            </Card>
          </ScrollReveal>

          <ScrollReveal delay={220}>
            <Card>
              <h2 className="text-lg font-bold text-text">Latest scan comparison</h2>
              <div className="mt-4"><ScanComparison items={historyState.items} /></div>
            </Card>
          </ScrollReveal>

          <ScrollReveal delay={260}>
            <Card>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-text">Recent scans</h2>
                <p className="text-xs text-text2">Page {historyState.page} of {historyState.pages}</p>
              </div>
              <div className="mt-4 space-y-3">
                {historyState.items.map((scan) => (
                  <Link key={scan.scan_id} to={APP_ROUTES.results.replace(":scanId", scan.scan_id)} className="block rounded-[20px] border border-border bg-bg3/80 p-4 transition-colors hover:border-[color:var(--border-strong)] hover:bg-bg2">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-mono text-xs text-text2">{scan.scan_id}</p>
                        <p className="mt-1 text-sm text-text">{scan.input_type.toUpperCase()} scan</p>
                        <p className="mt-1 text-xs text-text2">Findings: {scan.total_findings ?? "n/a"} | Score: {scan.health_score ?? "n/a"}</p>
                      </div>
                      <Badge severity={scan.status === "complete" ? "low" : scan.status === "error" ? "critical" : "medium"}>{scan.status}</Badge>
                    </div>
                  </Link>
                ))}
              </div>
              <div className="mt-4 flex items-center justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setHistoryState((prev) => ({ ...prev, page: Math.max(1, prev.page - 1) }))} disabled={historyState.page <= 1}>Previous</Button>
                <Button variant="ghost" size="sm" onClick={() => setHistoryState((prev) => ({ ...prev, page: Math.min(prev.pages, prev.page + 1) }))} disabled={historyState.page >= historyState.pages}>Next</Button>
              </div>
            </Card>
          </ScrollReveal>
        </>
      ) : null}
    </main>
  );
};

export default DashboardPage;
