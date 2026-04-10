import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, ArrowRight, Clock3, ShieldAlert } from "lucide-react";

import Button from "../components/Common/Button";
import Badge from "../components/Common/Badge";
import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
import ScanComparison from "../components/History/ScanComparison";
import ScoreTimeline from "../components/History/ScoreTimeline";
import { getScanHistory } from "../services/scanService";
import { APP_ROUTES } from "../utils/constants";

const DashboardPage = () => {
  const [historyState, setHistoryState] = useState({
    loading: true,
    items: [],
    page: 1,
    pages: 1,
    error: "",
  });

  useEffect(() => {
    let cancelled = false;

    const loadHistory = async () => {
      setHistoryState((prev) => ({ ...prev, loading: true, error: "" }));
      try {
        const payload = await getScanHistory(historyState.page, 6);
        if (cancelled) {
          return;
        }
        setHistoryState((prev) => ({
          ...prev,
          loading: false,
          items: payload.items || [],
          pages: payload.pages || 1,
          page: payload.page || prev.page,
        }));
      } catch (error) {
        if (cancelled) {
          return;
        }
        setHistoryState((prev) => ({
          ...prev,
          loading: false,
          error: error?.message || "Unable to load scan history",
        }));
      }
    };

    loadHistory();

    return () => {
      cancelled = true;
    };
  }, [historyState.page]);

  const hasHistory = historyState.items.length > 0;
  const latest = historyState.items[0];

  return (
    <main className="space-y-5">
      <ScrollReveal className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="overflow-hidden">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">Command center</p>
          <h1 className="mt-4 text-4xl font-bold leading-tight text-text md:text-5xl">Track scan health and reopen work instantly.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-text2">
            Review the latest findings, compare score movement, and jump back into the scan workspace without digging through sparse lists.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to={APP_ROUTES.scan}>
              <Button>
                Start New Scan
                <ArrowRight size={16} />
              </Button>
            </Link>
          </div>
        </Card>

        <Card className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
          <div className="rounded-[20px] border border-border bg-bg3/70 p-4">
            <div className="flex items-center gap-2 text-text3">
              <Activity size={16} />
              <span className="text-[11px] uppercase tracking-[0.16em]">Latest score</span>
            </div>
            <p className="mt-4 text-4xl font-bold text-text">{latest?.health_score ?? "n/a"}</p>
          </div>
          <div className="rounded-[20px] border border-border bg-bg3/70 p-4">
            <div className="flex items-center gap-2 text-text3">
              <ShieldAlert size={16} />
              <span className="text-[11px] uppercase tracking-[0.16em]">Latest findings</span>
            </div>
            <p className="mt-4 text-4xl font-bold text-text">{latest?.total_findings ?? 0}</p>
          </div>
          <div className="rounded-[20px] border border-border bg-bg3/70 p-4 sm:col-span-2 xl:col-span-1">
            <div className="flex items-center gap-2 text-text3">
              <Clock3 size={16} />
              <span className="text-[11px] uppercase tracking-[0.16em]">Recent mode</span>
            </div>
            <p className="mt-4 text-xl font-semibold text-text">{latest?.input_type ? `${latest.input_type.toUpperCase()} scan` : "No scans yet"}</p>
          </div>
        </Card>
      </ScrollReveal>

      {historyState.loading ? (
        <Card>
          <p className="text-sm text-text2">Loading recent scans...</p>
        </Card>
      ) : null}

      {!historyState.loading && historyState.error ? (
        <Card>
          <p className="text-sm text-red">{historyState.error}</p>
        </Card>
      ) : null}

      {!historyState.loading && !historyState.error && !hasHistory ? (
        <Card>
          <h2 className="text-lg font-bold text-text">No scans yet</h2>
          <p className="mt-2 text-sm text-text2">
            Start your first scan to unlock your health timeline, severity trends, and issue insights.
          </p>
          <Link to={APP_ROUTES.scan} className="mt-4 inline-block">
            <Button>Run First Scan</Button>
          </Link>
        </Card>
      ) : null}

      {!historyState.loading && !historyState.error && hasHistory ? (
        <>
          <ScrollReveal delay={90}>
          <Card>
            <h2 className="text-lg font-bold text-text">Health Score Timeline</h2>
            <div className="mt-4">
              <ScoreTimeline items={historyState.items} />
            </div>
          </Card>
          </ScrollReveal>

          <ScrollReveal delay={130}>
          <Card>
            <h2 className="text-lg font-bold text-text">Latest Scan Comparison</h2>
            <div className="mt-4">
              <ScanComparison items={historyState.items} />
            </div>
          </Card>
          </ScrollReveal>

          <ScrollReveal delay={170}>
          <Card>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-text">Recent Scans</h2>
              <p className="text-xs text-text2">Page {historyState.page} of {historyState.pages}</p>
            </div>

            <div className="mt-4 space-y-3">
              {historyState.items.map((scan) => (
                <Link
                  key={scan.scan_id}
                  to={APP_ROUTES.results.replace(":scanId", scan.scan_id)}
                  className="block rounded-[20px] border border-border bg-bg3/80 p-4 transition-colors hover:border-[color:var(--border-strong)] hover:bg-bg2"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-xs text-text2">{scan.scan_id}</p>
                      <p className="mt-1 text-sm text-text">{scan.input_type.toUpperCase()} scan</p>
                      <p className="mt-1 text-xs text-text2">Findings: {scan.total_findings ?? "n/a"} | Score: {scan.health_score ?? "n/a"}</p>
                    </div>
                    <Badge severity={scan.status === "complete" ? "low" : scan.status === "error" ? "critical" : "medium"}>
                      {scan.status}
                    </Badge>
                  </div>
                </Link>
              ))}
            </div>

            <div className="mt-4 flex items-center justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setHistoryState((prev) => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
                disabled={historyState.page <= 1}
              >
                Previous
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setHistoryState((prev) => ({ ...prev, page: Math.min(prev.pages, prev.page + 1) }))}
                disabled={historyState.page >= historyState.pages}
              >
                Next
              </Button>
            </div>
          </Card>
          </ScrollReveal>
        </>
      ) : null}
    </main>
  );
};

export default DashboardPage;
