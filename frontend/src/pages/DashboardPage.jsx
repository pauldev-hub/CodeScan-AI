import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Button from "../components/Common/Button";
import Badge from "../components/Common/Badge";
import Card from "../components/Common/Card";
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

  return (
    <main className="space-y-4">
      <Card>
        <h1 className="text-2xl font-bold text-text">Dashboard</h1>
        <p className="mt-2 text-sm text-text2">Track scan health over time and continue from your latest results.</p>
        <Link to={APP_ROUTES.scan} className="mt-4 inline-block">
          <Button>Start New Scan</Button>
        </Link>
      </Card>

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
          <Card>
            <h2 className="text-lg font-bold text-text">Health Score Timeline</h2>
            <div className="mt-4">
              <ScoreTimeline items={historyState.items} />
            </div>
          </Card>

          <Card>
            <h2 className="text-lg font-bold text-text">Latest Scan Comparison</h2>
            <div className="mt-4">
              <ScanComparison items={historyState.items} />
            </div>
          </Card>

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
                  className="block rounded-lg border border-border bg-bg3 p-3 transition-colors hover:bg-bg2"
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
        </>
      ) : null}
    </main>
  );
};

export default DashboardPage;
