import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MessageSquare, RotateCcw, SendHorizonal, Sparkles, X } from "lucide-react";
import { useLocation, useParams } from "react-router-dom";

import ChatBoundary from "../components/Chat/ChatBoundary";
import ConnectionStatusDot from "../components/Chat/ConnectionStatusDot";
import ErrorBoundary from "../components/Common/ErrorBoundary";
import Panel from "../components/Common/Panel";
import ScrollReveal from "../components/Common/ScrollReveal";
import { ChatBubbleSkeleton, FindingCardSkeleton, ScoreRingSkeleton, StatCardSkeleton } from "../components/Common/Skeletons";
import BeginnerModeToggle from "../components/Results/BeginnerModeToggle";
import CodeDiffView from "../components/Results/CodeDiffView";
import ExportShareBar from "../components/Results/ExportShareBar";
import FixThisButton from "../components/Results/FixThisButton";
import IssueDetail from "../components/Results/IssueDetail";
import ScoreRing from "../components/Results/ScoreRing";
import SeverityStatCard from "../components/Results/SeverityStatCard";
import { useAIChat } from "../hooks/useAIChat";
import { useBeginnerMode } from "../hooks/useBeginnerMode";
import { useScanStatus } from "../hooks/useScanStatus";
import { requestFixPreview } from "../services/fixService";
import { getScanResults } from "../services/scanService";
import { acquireLock, releaseLock } from "../utils/storage";

const ResultsPage = () => {
  const { scanId } = useParams();
  const location = useLocation();
  const { messages, status, sendMessage, isStreaming, scanCompleteEvent, clearMessages } = useAIChat(scanId);
  const { beginnerMode, toggleBeginnerMode } = useBeginnerMode();
  const [draft, setDraft] = useState("");
  const [results, setResults] = useState(null);
  const [resultsLoading, setResultsLoading] = useState(true);
  const [resultsError, setResultsError] = useState("");
  const [fixState, setFixState] = useState({
    loadingFor: null,
    byFinding: {},
    errorFor: {},
  });
  const [chatOpen, setChatOpen] = useState(false);
  const [isDesktopChat, setIsDesktopChat] = useState(() => window.matchMedia("(min-width: 1280px)").matches);
  const messagesRef = useRef(null);

  const fetchResults = useCallback(async () => {
    setResultsLoading(true);
    try {
      const payload = await getScanResults(scanId);
      setResults(payload);
      setResultsError("");
    } catch (error) {
      if (error?.status === 404) {
        setResults(null);
      } else {
        setResultsError(error?.message || "Unable to load scan results");
      }
    } finally {
      setResultsLoading(false);
    }
  }, [scanId]);

  const statusState = useScanStatus(scanId, {
    enabled: !results,
    pollMs: location.state?.justSubmitted ? 1800 : 2500,
    maxDurationMs: 8 * 60 * 1000,
    onComplete: () => {
      fetchResults();
    },
  });

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  useEffect(() => {
    if (scanCompleteEvent?.scan_id === scanId) {
      fetchResults();
    }
  }, [fetchResults, scanCompleteEvent, scanId]);

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1280px)");
    const onChange = (event) => {
      setIsDesktopChat(event.matches);
      if (event.matches) {
        setChatOpen(false);
      }
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (!messagesRef.current) {
      return;
    }
    messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
  }, [messages]);

  const onSend = () => {
    if (!draft.trim()) {
      return;
    }
    sendMessage(draft);
    setDraft("");
  };

  const onComposerKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  const statusCopy = useMemo(() => {
    if (status === "connected") {
      return "Connected to the scan room";
    }
    if (status === "reconnecting") {
      return "Reconnecting to chat";
    }
    if (status === "disconnected") {
      return "Chat is offline for the moment";
    }
    return "Connecting to AI assistant";
  }, [status]);

  const onGenerateFix = async (finding) => {
    if (!finding?.id || fixState.loadingFor) {
      return;
    }

    const lockKey = `codescan:fix-lock:${scanId}:${finding.id}`;
    if (!acquireLock(lockKey, 2500)) {
      return;
    }

    setFixState((prev) => ({ ...prev, loadingFor: finding.id }));
    try {
      const preview = await requestFixPreview({ scanId, finding });
      setFixState((prev) => ({
        loadingFor: null,
        byFinding: {
          ...prev.byFinding,
          [finding.id]: preview,
        },
        errorFor: {
          ...prev.errorFor,
          [finding.id]: preview?.source === "fallback" ? preview.message : "",
        },
      }));
    } finally {
      releaseLock(lockKey);
    }
  };

  const ChatPanel = ({ onClose }) => (
    <aside className="codescan-glass rounded-[26px] bg-[color:var(--panel)] p-4">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <p className="text-sm font-semibold">AI Chat</p>
          <p className="mt-1 text-xs text-text2">{statusCopy}</p>
        </div>
        <div className="flex items-center gap-2">
          <ConnectionStatusDot status={status} />
          <button
            type="button"
            onClick={clearMessages}
            className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-border bg-bg3 text-text"
            aria-label="Clear chat"
          >
            <RotateCcw size={14} />
          </button>
          {onClose ? (
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-border bg-bg3 text-text"
              aria-label="Close chat"
            >
              <X size={14} />
            </button>
          ) : null}
        </div>
      </div>

      <div ref={messagesRef} className="codescan-chat-scroll mt-4 flex max-h-[420px] min-h-[320px] flex-col gap-3 overflow-auto pr-1">
        {!messages.length ? <ChatBubbleSkeleton /> : null}
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`max-w-[92%] whitespace-pre-line rounded-2xl px-4 py-3 text-sm leading-6 ${
              message.role === "user"
                ? "ml-auto bg-[linear-gradient(135deg,var(--accent),var(--accent-2))] text-[#23150c]"
                : message.role === "system"
                  ? "border border-border bg-bg3/70 text-text2"
                  : "bg-bg3 text-text"
            }`}
          >
            {message.role === "assistant" ? (
              <div className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-text3">
                <Sparkles size={12} className="text-accent" />
                Assistant
              </div>
            ) : null}
            {message.text}
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-[22px] border border-border bg-bg3/70 p-3">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onComposerKeyDown}
          className="min-h-[92px] w-full resize-none border-0 bg-transparent px-1 py-1 text-sm text-text outline-none placeholder:text-text3"
          placeholder="Ask about the highest risk, request a safer fix, or ask what to prioritize first."
        />
        <div className="mt-3 flex items-center justify-between gap-3 border-t border-border pt-3">
          <p className="text-xs text-text2">Press Enter to send. Use Shift+Enter for a new line.</p>
          <button
            type="button"
            onClick={onSend}
            disabled={!draft.trim() || isStreaming}
            className="inline-flex items-center gap-2 rounded-xl border border-[color:var(--accent)] bg-[linear-gradient(135deg,var(--accent),var(--accent-2))] px-4 py-2 text-sm font-semibold text-[#23150c] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <SendHorizonal size={14} />
            Send
          </button>
        </div>
      </div>

      {isStreaming ? <p className="mt-2 text-xs text-text2">AI is typing...</p> : null}
    </aside>
  );

  return (
    <main className="space-y-5">
      {!isDesktopChat ? (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => setChatOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-bg2 px-3 py-2 text-sm font-semibold text-text"
          >
            <MessageSquare size={16} />
            Open AI Chat
          </button>
        </div>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <ErrorBoundary>
          <section className="space-y-4">
          <ScrollReveal>
          <Panel title="Scan Overview" description={`Scan: ${scanId}`}>
            {resultsLoading && !results ? (
              <div className="grid gap-4 md:grid-cols-[120px_1fr]">
                <ScoreRingSkeleton />
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <StatCardSkeleton />
                  <StatCardSkeleton />
                  <StatCardSkeleton />
                  <StatCardSkeleton />
                </div>
              </div>
            ) : null}

            {!results && !resultsLoading ? (
              <div className="space-y-3">
                <p className="text-sm text-text2">
                  Status: <span className="font-semibold text-text">{statusState.status}</span>
                </p>
                <div className="h-2 w-full overflow-hidden rounded-full bg-bg3">
                  <div className="h-full bg-accent transition-all duration-300" style={{ width: `${Math.max(5, statusState.progress || 0)}%` }} />
                </div>
                {statusState.error ? <p className="text-sm text-red">{statusState.error.message || "Polling error"}</p> : null}
                {statusState.timedOut ? (
                  <button type="button" className="rounded-lg border border-border bg-bg3 px-3 py-2 text-sm" onClick={fetchResults}>
                    Retry Loading Results
                  </button>
                ) : null}
              </div>
            ) : null}

            {results ? (
              <div className="grid gap-4 md:grid-cols-[120px_1fr]">
                <ScoreRing score={results.health_score ?? 0} />
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <SeverityStatCard label={beginnerMode ? "Issues Found" : "Total Findings"} value={results.summary?.total_findings ?? 0} />
                  <SeverityStatCard label={beginnerMode ? "Urgent" : "Critical"} value={results.summary?.critical_count ?? 0} className="text-red" />
                  <SeverityStatCard label={beginnerMode ? "Important" : "High"} value={results.summary?.high_count ?? 0} className="text-yellow" />
                  <SeverityStatCard label={beginnerMode ? "Worth Fixing" : "Medium"} value={results.summary?.medium_count ?? 0} className="text-purple" />
                  <SeverityStatCard label={beginnerMode ? "Minor" : "Low"} value={results.summary?.low_count ?? 0} className="text-green" />
                  <SeverityStatCard label={beginnerMode ? "Scan Time (sec)" : "Scan Time"} value={results.analysis_time_seconds ?? 0} />
                </div>
              </div>
            ) : null}
          </Panel>
          </ScrollReveal>

          <ScrollReveal delay={90}>
          <Panel title="Findings" description="Result cards and explanations load here.">
            <div className="mb-3 flex items-center justify-end">
              <BeginnerModeToggle enabled={beginnerMode} onToggle={toggleBeginnerMode} />
            </div>

            {resultsError ? <p className="text-sm text-red">{resultsError}</p> : null}

            {resultsLoading && !results ? (
              <div className="space-y-3">
                <FindingCardSkeleton />
                <FindingCardSkeleton />
              </div>
            ) : null}

            {results && results.findings?.length ? (
              <div className="space-y-3">
                {results.findings.map((finding) => (
                  <div key={finding.id} className="space-y-2">
                    <IssueDetail finding={finding} beginnerMode={beginnerMode} />

                    <div className="flex items-center justify-end">
                      <FixThisButton
                        loading={fixState.loadingFor === finding.id}
                        disabled={Boolean(fixState.loadingFor && fixState.loadingFor !== finding.id)}
                        onClick={() => onGenerateFix(finding)}
                      />
                    </div>

                    {fixState.errorFor[finding.id] ? (
                      <p className="text-xs text-yellow">{fixState.errorFor[finding.id]}</p>
                    ) : null}

                    {fixState.byFinding[finding.id] ? (
                      <CodeDiffView
                        before={fixState.byFinding[finding.id].before}
                        after={fixState.byFinding[finding.id].after}
                        language="javascript"
                      />
                    ) : null}
                  </div>
                ))}
              </div>
            ) : null}

            {results && !results.findings?.length ? (
              <p className="text-sm text-text2">No findings were detected for this scan.</p>
            ) : null}
          </Panel>
          </ScrollReveal>

          {results ? (
            <ScrollReveal delay={130}>
            <Panel title="Export & Share" description="Download reports or create a shareable public link.">
              <ExportShareBar scanId={scanId} />
            </Panel>
            </ScrollReveal>
          ) : null}
          </section>
        </ErrorBoundary>

        {isDesktopChat ? (
          <ChatBoundary>
            <div className="xl:sticky xl:top-[84px]">
              <ChatPanel />
            </div>
          </ChatBoundary>
        ) : null}
      </div>

      {!isDesktopChat ? (
        <div className={`fixed inset-0 z-40 ${chatOpen ? "" : "pointer-events-none"}`}>
          <button
            type="button"
            onClick={() => setChatOpen(false)}
            className={`absolute inset-0 bg-black/30 transition-opacity duration-300 ${chatOpen ? "opacity-100" : "opacity-0"}`}
            aria-label="Close chat drawer"
          />
          <div
            className={`absolute right-0 top-0 h-full w-full max-w-[360px] p-3 transition-transform duration-300 ${
              chatOpen ? "translate-x-0" : "translate-x-full"
            }`}
          >
            <ChatBoundary>
              <div className="h-full overflow-auto">
                <ChatPanel onClose={() => setChatOpen(false)} />
              </div>
            </ChatBoundary>
          </div>
        </div>
      ) : null}
    </main>
  );
};

export default ResultsPage;
