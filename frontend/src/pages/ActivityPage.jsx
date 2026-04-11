import { Link } from "react-router-dom";
import { Clock3, RefreshCcw, Share2, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
import { createShareLink } from "../services/reportService";
import { deleteScan, getScanHistory } from "../services/scanService";
import { APP_ROUTES } from "../utils/constants";

const formatDateTime = (value) => {
  if (!value) {
    return "n/a";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "n/a";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
};

const ActivityPage = () => {
  const [state, setState] = useState({ loading: true, error: "", items: [] });

  const load = async () => {
    setState((prev) => ({ ...prev, loading: true, error: "" }));
    try {
      const payload = await getScanHistory(1, 20);
      setState({ loading: false, error: "", items: payload.items || [] });
    } catch (error) {
      setState({ loading: false, error: error?.message || "Unable to load activity", items: [] });
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onDelete = async (scanId) => {
    await deleteScan(scanId);
    await load();
  };

  const onShare = async (scanId) => {
    await createShareLink(scanId);
  };

  return (
    <main className="space-y-5">
      <ScrollReveal className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-accent">Activity</p>
          <h1 className="mt-4 text-4xl font-bold leading-tight text-text md:text-5xl">Track scans, failures, queue mode, and where to jump back in.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-text2">
            This feed is separate from the dashboard so scan operations, retries, and quick actions stay easy to manage.
          </p>
        </Card>
        <Card className="bg-[linear-gradient(135deg,rgba(214,161,108,0.16),rgba(255,255,255,0.02))]">
          <div className="flex items-center gap-2 text-accent">
            <Clock3 size={16} />
            <span className="text-[11px] uppercase tracking-[0.18em]">Feed summary</span>
          </div>
          <p className="mt-4 text-sm leading-7 text-text2">Recent scans show runtime mode and provider details, so worker and fallback behavior are visible instead of hidden.</p>
        </Card>
      </ScrollReveal>

      {state.loading ? <Card>Loading activity...</Card> : null}
      {state.error ? <Card>{state.error}</Card> : null}

      {!state.loading && !state.error ? (
        <div className="space-y-3">
          {state.items.map((scan) => (
            <ScrollReveal key={scan.scan_id}>
              <Card className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-mono text-xs text-text3">{scan.scan_id}</p>
                  <p className="mt-1 text-sm font-semibold text-text">{scan.input_type?.toUpperCase()} scan</p>
                  <p className="mt-1 text-xs text-text2">
                    Status: {scan.status} | Score: {scan.health_score ?? "n/a"} | Findings: {scan.total_findings ?? "n/a"}
                  </p>
                  <p className="mt-1 text-xs text-text2">
                    Queue: {scan.queue_mode || "unknown"} | Provider: {scan.provider_used || "local_fallback"}
                  </p>
                  <p className="mt-1 text-xs text-text2">
                    Started: {formatDateTime(scan.created_at)} | Finished: {formatDateTime(scan.completed_at)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link to={APP_ROUTES.results.replace(":scanId", scan.scan_id)}>
                    <Button size="sm" variant="ghost">Open</Button>
                  </Link>
                  <Button size="sm" variant="ghost" onClick={() => load()}>
                    <RefreshCcw size={14} />
                    Refresh
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => onShare(scan.scan_id)}>
                    <Share2 size={14} />
                    Share
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => onDelete(scan.scan_id)}>
                    <Trash2 size={14} />
                    Delete
                  </Button>
                </div>
              </Card>
            </ScrollReveal>
          ))}
          {!state.items.length ? <Card>No scan activity yet.</Card> : null}
        </div>
      ) : null}
    </main>
  );
};

export default ActivityPage;
