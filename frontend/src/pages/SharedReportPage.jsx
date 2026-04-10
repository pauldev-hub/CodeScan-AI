import axios from "axios";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Globe2, ShieldCheck } from "lucide-react";

import Badge from "../components/Common/Badge";
import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
import { API_BASE_URL, API_PATHS } from "../utils/constants";

const publicClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

const labelForStatus = (status) => {
  if (status === 404) {
    return {
      title: "Shared report not found",
      description: "This link does not exist. Verify the URL or ask the owner to generate a new one.",
    };
  }
  if (status === 410) {
    return {
      title: "Shared report expired or revoked",
      description: "The owner disabled this link or its access period ended.",
    };
  }
  return {
    title: "Shared report unavailable",
    description: "This report is temporarily unavailable. Please retry shortly.",
  };
};

const SharedReportPage = () => {
  const { shareUuid } = useParams();
  const [state, setState] = useState({ loading: true, payload: null, error: null, status: null });

  useEffect(() => {
    let cancelled = false;

    const fetchShared = async () => {
      try {
        const response = await publicClient.get(API_PATHS.sharedReport(shareUuid));
        if (!cancelled) {
          setState({ loading: false, payload: response.data, error: null, status: 200 });
        }
      } catch (error) {
        const status = error?.response?.status;
        const message = error?.response?.data?.error || error.message;
        if (!cancelled) {
          setState({ loading: false, payload: null, error: message, status });
        }
      }
    };

    fetchShared();

    return () => {
      cancelled = true;
    };
  }, [shareUuid]);

  if (state.loading) {
    return (
      <main className="mx-auto w-[min(1480px,calc(100vw-24px))] px-3 py-8 md:px-4 md:py-10">
        <Card>Loading shared report...</Card>
      </main>
    );
  }

  if (state.status === 404 || state.status === 410) {
    const unavailable = labelForStatus(state.status);
    return (
      <main className="mx-auto w-[min(1480px,calc(100vw-24px))] px-3 py-8 md:px-4 md:py-10">
        <Card>
          <h1 className="text-xl font-bold">{unavailable.title}</h1>
          <p className="mt-2 text-sm text-text2">{unavailable.description}</p>
        </Card>
      </main>
    );
  }

  if (state.error && !state.payload) {
    const unavailable = labelForStatus(state.status);
    return (
      <main className="mx-auto w-[min(1480px,calc(100vw-24px))] px-3 py-8 md:px-4 md:py-10">
        <Card>
          <h1 className="text-xl font-bold">{unavailable.title}</h1>
          <p className="mt-2 text-sm text-text2">{state.error}</p>
        </Card>
      </main>
    );
  }

  return (
    <main className="mx-auto w-[min(1480px,calc(100vw-24px))] px-3 py-8 md:px-4 md:py-10">
      <div className="space-y-5">
        <ScrollReveal className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <div className="flex items-center gap-2 text-accent">
            <Globe2 size={16} />
            <span className="font-mono text-xs uppercase tracking-[0.18em]">Public report</span>
          </div>
          <h1 className="text-xl font-bold">Shared Report</h1>
          <p className="mt-2 text-sm text-text2">Health Score: {state.payload?.health_score ?? "n/a"}</p>
          <p className="mt-1 text-xs text-text2">Read-only report view</p>
        </Card>
        <Card>
          <div className="flex items-center gap-2 text-accent">
            <ShieldCheck size={16} />
            <span className="font-mono text-xs uppercase tracking-[0.18em]">Snapshot</span>
          </div>
          <p className="mt-3 text-sm leading-7 text-text2">
            This shared view is safe for review-only access. It preserves the scan summary and findings without exposing workspace controls.
          </p>
        </Card>
        </ScrollReveal>

        <ScrollReveal delay={120}>
        <Card>
          <h2 className="text-lg font-bold">Findings</h2>
          {state.payload?.findings?.length ? (
            <div className="mt-4 grid gap-3 xl:grid-cols-2">
              {state.payload.findings.map((finding) => (
                <article key={finding.id} className="rounded-[22px] border border-border bg-bg3/80 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-text">{finding.title}</p>
                      <p className="mt-1 text-xs text-text2">{finding.file_path}:{finding.line_number || "n/a"}</p>
                    </div>
                    <Badge severity={(finding.severity || "low").toLowerCase()}>{finding.severity}</Badge>
                  </div>
                  <p className="mt-2 text-sm text-text2">{finding.plain_english || finding.description}</p>
                  <p className="mt-2 text-xs text-text2">Exploit risk: {finding.exploit_risk ?? 0}%</p>
                </article>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-text2">No findings were included in this report.</p>
          )}
        </Card>
        </ScrollReveal>
      </div>
    </main>
  );
};

export default SharedReportPage;
