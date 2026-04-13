import { useCallback, useEffect, useMemo, useState } from "react";
import { MessageSquare, Sparkles } from "lucide-react";
import { useLocation, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";

import ChatBoundary from "../components/Chat/ChatBoundary";
import DevChatPanel from "../components/Chat/DevChatPanel";
import ErrorBoundary from "../components/Common/ErrorBoundary";
import Panel from "../components/Common/Panel";
import ScrollReveal from "../components/Common/ScrollReveal";
import Tabs from "../components/Common/Tabs";
import { FindingCardSkeleton, ScoreRingSkeleton, StatCardSkeleton } from "../components/Common/Skeletons";
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
import { getScanResults, regenerateLearnContent } from "../services/scanService";
import { formatDateTimeInIndia } from "../utils/datetime";
import { acquireLock, releaseLock } from "../utils/storage";

const resultTabs = [
  { value: "overview", label: "Overview" },
  { value: "security", label: "Security" },
  { value: "map", label: "Map" },
  { value: "dependencies", label: "Dependencies" },
  { value: "learn", label: "Learn" },
];

const runAttackDemo = (finding, payload) => {
  const normalizedPayload = (payload || "").trim() || finding?.live_simulator?.placeholder || "' OR '1'='1";
  const title = (finding?.title || "").toLowerCase();
  if (title.includes("xss")) {
    return {
      verdict: normalizedPayload.includes("<script") || normalizedPayload.includes("onerror")
        ? "Unsafe HTML rendering would execute this payload in the browser."
        : "This payload looks harmless, but unsafe rendering would still treat it as markup.",
      trace: [
        `Input received: ${normalizedPayload}`,
        "App inserts the string into the page without escaping.",
        "Browser parses the payload as active markup instead of plain text.",
      ],
    };
  }
  return {
    verdict: normalizedPayload.includes("or") || normalizedPayload.includes("union")
      ? "Unsafe query building would treat this payload as query logic instead of plain data."
      : "This payload is mild, but the unsafe query path would still keep the attacker in control of SQL structure.",
    trace: [
      `Input received: ${normalizedPayload}`,
      "App concatenates the payload into a database query.",
      "Database executes the modified query shape and may bypass filtering or leak rows.",
    ],
  };
};

const evaluateChallenge = (expectedKeywords = [], guess = "") => {
  const normalized = guess.toLowerCase();
  const matches = expectedKeywords.filter((keyword) => normalized.includes(keyword.toLowerCase()));
  return {
    isSuccess: matches.length > 0,
    score: matches.length,
  };
};

const toObjectList = (value) => (Array.isArray(value) ? value.filter((item) => item && typeof item === "object") : []);

const buildFallbackLearnTab = (findings = [], inputLanguage = "code") => {
  const topItems = findings.slice(0, 5);
  return {
    micro_lessons: topItems.map((item) => ({
      finding_id: item.id,
      title: item.title,
      lesson: item.teaching_focus || item.fix_suggestion || "Use safer patterns and validate inputs early.",
      story: `In ${inputLanguage}, this issue appears when input is trusted too early.`,
      fact: item.owasp_category || "A04: Insecure Design",
    })),
    quiz: topItems.map((item) => ({
      question: `Why is '${item.title}' risky here?`,
      answer: item.plain_english || item.description || item.fix_suggestion || "It can change app behavior in unsafe ways.",
      difficulty: "beginner",
    })),
    fix_it_yourself: topItems.map((item) => ({
      finding_id: item.id,
      prompt: `Rewrite the code path to avoid ${String(item.title || "this issue").toLowerCase()}.`,
      hint: item.fix_suggestion || "Use input validation and safer APIs.",
      success_criteria: "The risky behavior is removed without breaking intended behavior.",
    })),
    debate_starters: topItems.map((item) => ({
      finding_id: item.id,
      starter: `I think '${item.title}' might be mitigated because...`,
      coach_reply: "Point to concrete guards: validation, escaping, auth checks, or parameterization.",
    })),
    hacker_challenges: topItems.map((item) => ({
      finding_id: item.id,
      title: item.title,
      prompt: item.hacker_challenge?.prompt || `What payload would you try first against ${item.title}?`,
      hint: item.hacker_challenge?.hint || "Think about where untrusted input enters the code.",
      expected_keywords: item.hacker_challenge?.expected_keywords || ["payload", "input"],
      solution: item.hacker_challenge?.solution || item.fix_suggestion || "Constrain input and remove unsafe execution paths.",
    })),
    code_roasts: topItems.map((item) => ({
      finding_id: item.id,
      title: item.title,
      gentle: item.code_roast?.gentle || "This is fixable with safer defaults and one focused refactor.",
      brutal: item.code_roast?.brutal || "This path gives attackers too much leverage. Lock it down now.",
      teaching_point: item.code_roast?.teaching_point || item.fix_suggestion || "Prefer explicit validation and strict APIs.",
    })),
    live_attack_labs: topItems.map((item) => ({
      finding_id: item.id,
      title: item.title,
      label: item.live_simulator?.label || "Payload sandbox",
      placeholder: item.live_simulator?.placeholder || "Try a test payload",
      safe_default_payload: item.live_simulator?.safe_default_payload || item.live_simulator?.placeholder || "payload",
      expected_result: item.live_simulator?.expected_result || "Unsafe code may treat the payload as executable logic.",
      impact: item.live_simulator?.impact || "An attacker could influence behavior or expose sensitive data.",
    })),
    source: "frontend_fallback",
    generated_at: new Date().toISOString(),
  };
};

const ResultsPage = () => {
  const { scanId } = useParams();
  const location = useLocation();
  const { messages, status, sendMessage, isStreaming, scanCompleteEvent, clearMessages } = useAIChat({ scanId, autoCreate: true });
  const { beginnerMode, toggleBeginnerMode } = useBeginnerMode();
  const [draft, setDraft] = useState("");
  const [activeTab, setActiveTab] = useState("overview");
  const [results, setResults] = useState(null);
  const [resultsLoading, setResultsLoading] = useState(true);
  const [resultsError, setResultsError] = useState("");
  const [fixState, setFixState] = useState({ loadingFor: null, byFinding: {}, errorFor: {} });
  const [findingPanelState, setFindingPanelState] = useState({});
  const [chatOpen, setChatOpen] = useState(false);
  const [isDesktopChat, setIsDesktopChat] = useState(() => window.matchMedia("(min-width: 1280px)").matches);
  const [learnState, setLearnState] = useState({ loading: false, error: "" });
  const [roastMode, setRoastMode] = useState("gentle");
  const [challengeState, setChallengeState] = useState({});
  const [labState, setLabState] = useState({ payloads: {}, outputs: {} });

  const fetchResults = useCallback(async () => {
    setResultsLoading(true);
    try {
      const payload = await getScanResults(scanId);
      setResults(payload);
      setResultsError("");
    } catch (error) {
      setResultsError(error?.message || "Unable to load scan results");
    } finally {
      setResultsLoading(false);
    }
  }, [scanId]);

  const statusState = useScanStatus(scanId, {
    enabled: !results,
    pollMs: location.state?.justSubmitted ? 1800 : 2500,
    maxDurationMs: 8 * 60 * 1000,
    onComplete: fetchResults,
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

  const onSend = () => {
    if (!draft.trim()) {
      return;
    }
    sendMessage(draft);
    setDraft("");
  };

  const onQuickMessage = (message) => {
    setDraft(message);
    if (!isDesktopChat) {
      setChatOpen(true);
    }
    sendMessage(message);
  };

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
        byFinding: { ...prev.byFinding, [finding.id]: { originalAfter: preview.after, ...preview } },
        errorFor: { ...prev.errorFor, [finding.id]: preview?.source === "fallback" ? preview.message : "" },
      }));
    } finally {
      releaseLock(lockKey);
    }
  };

  const currentFindings = useMemo(() => {
    if (!results?.findings) return [];
    if (activeTab === "security") return results.tabs?.security?.findings || [];
    if (activeTab === "overview") return results.findings;
    return results.findings;
  }, [activeTab, results]);

  const overview = results?.tabs?.overview;
  const chartData = overview?.matrix || [];
  const fallbackLearnTab = useMemo(
    () => buildFallbackLearnTab(results?.findings || [], results?.input_language || "code"),
    [results]
  );
  const learnTab = useMemo(() => {
    const raw = results?.tabs?.learn || {};
    return {
      micro_lessons: toObjectList(raw.micro_lessons).length ? toObjectList(raw.micro_lessons) : fallbackLearnTab.micro_lessons,
      quiz: toObjectList(raw.quiz).length ? toObjectList(raw.quiz) : fallbackLearnTab.quiz,
      fix_it_yourself: toObjectList(raw.fix_it_yourself).length ? toObjectList(raw.fix_it_yourself) : fallbackLearnTab.fix_it_yourself,
      debate_starters: toObjectList(raw.debate_starters).length ? toObjectList(raw.debate_starters) : fallbackLearnTab.debate_starters,
      hacker_challenges: toObjectList(raw.hacker_challenges).length ? toObjectList(raw.hacker_challenges) : fallbackLearnTab.hacker_challenges,
      code_roasts: toObjectList(raw.code_roasts).length ? toObjectList(raw.code_roasts) : fallbackLearnTab.code_roasts,
      live_attack_labs: toObjectList(raw.live_attack_labs).length ? toObjectList(raw.live_attack_labs) : fallbackLearnTab.live_attack_labs,
      source: raw.source || fallbackLearnTab.source,
      generated_at: raw.generated_at || fallbackLearnTab.generated_at,
    };
  }, [results, fallbackLearnTab]);
  const hasLearnContent = useMemo(() => {
    const collections = [
      learnTab.micro_lessons,
      learnTab.quiz,
      learnTab.fix_it_yourself,
      learnTab.debate_starters,
      learnTab.code_roasts,
      learnTab.hacker_challenges,
      learnTab.live_attack_labs,
    ];
    return collections.some((items) => Array.isArray(items) && items.length > 0);
  }, [learnTab]);
  const dependencyTab = results?.tabs?.dependencies || {};
  const resultsQuickPrompts = useMemo(() => {
    const starters = Array.isArray(results?.chat_starters) ? results.chat_starters.map((item) => item.message).filter(Boolean) : [];
    return starters.length ? starters : [
      "Explain the highest-risk issue in plain English.",
      "What should I fix first and why?",
      "Search code for auth middleware",
      "Roast this code gently.",
    ];
  }, [results]);

  const onGenerateLearn = async () => {
    if (!scanId) {
      return;
    }
    setLearnState({ loading: true, error: "" });
    try {
      await regenerateLearnContent(scanId);
      await fetchResults();
      setLearnState({ loading: false, error: "" });
    } catch (error) {
      setLearnState({ loading: false, error: error?.message || "Unable to generate learn content" });
    }
  };

  const onOpenFindingPanel = (finding, panel) => {
    setFindingPanelState((prev) => ({
      ...prev,
      [finding.id]: {
        ...prev[finding.id],
        panel,
      },
    }));
    if (!isDesktopChat) {
      setChatOpen(true);
    }
  };

  const onRunFindingSimulation = (finding) => {
    const payload =
      findingPanelState[finding.id]?.payload ||
      finding?.live_simulator?.safe_default_payload ||
      finding?.live_simulator?.placeholder ||
      "' OR '1'='1";
    const output = runAttackDemo(finding, payload);
    setFindingPanelState((prev) => ({
      ...prev,
      [finding.id]: {
        ...prev[finding.id],
        panel: "attack",
        payload,
        output,
      },
    }));
  };

  const onUpdateFixCode = (findingId, value) => {
    setFixState((prev) => ({
      ...prev,
      byFinding: {
        ...prev.byFinding,
        [findingId]: {
          ...prev.byFinding[findingId],
          after: value,
        },
      },
    }));
  };

  const onResetFixCode = (findingId) => {
    setFixState((prev) => ({
      ...prev,
      byFinding: {
        ...prev.byFinding,
        [findingId]: {
          ...prev.byFinding[findingId],
          after: prev.byFinding[findingId]?.originalAfter || "",
        },
      },
    }));
  };

  return (
    <main className="space-y-5">
      {!isDesktopChat ? <div className="flex justify-end"><button type="button" onClick={() => setChatOpen(true)} className="inline-flex items-center gap-2 rounded-lg border border-border bg-bg2 px-3 py-2 text-sm font-semibold text-text"><MessageSquare size={16} />Open AI Chat</button></div> : null}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <ErrorBoundary>
          <section className="space-y-4">
            <ScrollReveal>
              <Panel title="Results Hub" description={`Scan ${scanId}`}>
                {resultsLoading && !results ? <div className="grid gap-4 md:grid-cols-[120px_1fr]"><ScoreRingSkeleton /><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><StatCardSkeleton /><StatCardSkeleton /><StatCardSkeleton /><StatCardSkeleton /></div></div> : null}
                {!results && !resultsLoading ? (
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-sm text-text2">
                        Status: <span className="font-semibold text-text">{statusState.status}</span>
                      </p>
                      <span className="rounded-full border border-border bg-bg3 px-3 py-1 text-xs text-text2">
                        {Math.max(5, statusState.progress || 0)}% complete
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-bg3">
                      <div className="h-full bg-accent transition-all duration-300" style={{ width: `${Math.max(5, statusState.progress || 0)}%` }} />
                    </div>
                    <div className="grid gap-3 md:grid-cols-3">
                      <div className="rounded-2xl border border-border bg-bg3/60 p-4">
                        <div className="h-3 w-20 animate-pulse rounded bg-bg4" />
                        <div className="mt-3 h-8 w-28 animate-pulse rounded bg-bg4" />
                      </div>
                      <div className="rounded-2xl border border-border bg-bg3/60 p-4">
                        <div className="h-3 w-24 animate-pulse rounded bg-bg4" />
                        <div className="mt-3 h-8 w-32 animate-pulse rounded bg-bg4" />
                      </div>
                      <div className="rounded-2xl border border-border bg-bg3/60 p-4">
                        <div className="h-3 w-16 animate-pulse rounded bg-bg4" />
                        <div className="mt-3 h-8 w-20 animate-pulse rounded bg-bg4" />
                      </div>
                    </div>
                    <p className="text-sm text-text2">Preparing findings, dependency clues, and guided learning blocks for this scan.</p>
                  </div>
                ) : null}
                {results ? <div className="space-y-4"><div className="grid gap-4 lg:grid-cols-[140px_minmax(0,1fr)]"><ScoreRing score={results.health_score ?? 0} /><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><SeverityStatCard label="Findings" value={results.summary?.total_findings ?? 0} /><SeverityStatCard label="Critical" value={results.summary?.critical_count ?? 0} className="text-red" /><SeverityStatCard label="Complexity" value={results.summary?.complexity_score ?? 0} /><SeverityStatCard label="Fix Time (min)" value={results.summary?.fix_time_total_minutes ?? 0} /></div></div><div className="flex flex-wrap gap-3 text-xs text-text2"><span className="rounded-full border border-border bg-bg3 px-3 py-1.5">Provider: {results.provider_used || "local_fallback"}</span><span className="rounded-full border border-border bg-bg3 px-3 py-1.5">Started: {formatDateTimeInIndia(results.created_at)}</span><span className="rounded-full border border-border bg-bg3 px-3 py-1.5">Finished: {formatDateTimeInIndia(results.completed_at)}</span></div></div> : null}
              </Panel>
            </ScrollReveal>

            {results ? (
              <>
                <ScrollReveal delay={70}>
                  <Panel title="Workspace Controls" description="Switch between results modes without leaving the page.">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <Tabs tabs={resultTabs} activeTab={activeTab} onChange={setActiveTab} />
                      <div className="flex items-center gap-3">
                        <BeginnerModeToggle enabled={beginnerMode} onToggle={toggleBeginnerMode} />
                        <span className="rounded-full border border-border bg-bg3 px-3 py-1.5 text-xs text-text2">{results.input_language}</span>
                      </div>
                    </div>
                  </Panel>
                </ScrollReveal>

                {activeTab === "overview" ? (
                  <ScrollReveal delay={100}>
                    <Panel title="Overview" description="Prioritized risk, effort, and the main findings list.">
                      {overview?.secret_banner ? <div className="mb-4 rounded-2xl border border-red/40 bg-red/10 p-4 text-sm text-text">Secret or credential leak warning: {overview.secret_banner.title}</div> : null}
                      <div className="grid gap-4 lg:grid-cols-2">
                        <div className="rounded-[24px] border border-border bg-bg3/70 p-4">
                          <p className="text-sm font-semibold text-text">Risk vs effort matrix</p>
                          <div className="mt-4 h-[280px]"><ResponsiveContainer width="100%" height="100%"><ScatterChart><CartesianGrid stroke="var(--border)" /><XAxis type="number" dataKey="effort" name="Effort" stroke="var(--text2)" /><YAxis type="number" dataKey="risk" name="Risk" stroke="var(--text2)" /><Tooltip cursor={{ strokeDasharray: "3 3" }} /><Scatter data={chartData} fill="var(--accent)" /></ScatterChart></ResponsiveContainer></div>
                        </div>
                        <div className="rounded-[24px] border border-border bg-bg3/70 p-4">
                          <p className="text-sm font-semibold text-text">Fix priority queue</p>
                          <div className="mt-4 space-y-3">{(overview?.priority_queue || []).map((item) => <div key={item.id} className="rounded-2xl border border-border bg-bg2 px-4 py-3"><p className="text-sm font-semibold text-text">{item.title}</p><p className="mt-1 text-xs text-text2">{item.priority_label} | {item.fix_time_minutes} min | {item.owasp_category}</p></div>)}</div>
                        </div>
                      </div>
                    </Panel>
                  </ScrollReveal>
                ) : null}

                {activeTab === "security" ? <ScrollReveal delay={100}><Panel title="Security" description="Threat warnings, attack examples, and security-focused findings."><div className="grid gap-3 md:grid-cols-2">{(results.tabs?.security?.findings || []).map((item) => <div key={item.id} className="rounded-[24px] border border-border bg-bg3/70 p-4"><p className="text-sm font-semibold text-text">{item.title}</p><p className="mt-2 text-sm text-text2">{item.attack_example}</p><p className="mt-2 text-xs text-text3">Exploit difficulty: {item.exploit_difficulty}/100</p><div className="mt-3 rounded-2xl border border-border bg-bg2 p-3"><p className="text-xs uppercase tracking-[0.14em] text-text3">{item.live_simulator?.label}</p><p className="mt-2 text-sm text-text2">{item.live_simulator?.placeholder}</p></div></div>)}</div></Panel></ScrollReveal> : null}
                {activeTab === "map" ? <ScrollReveal delay={100}><Panel title="Map" description="Heat map, dead code signal, and duplication hints."><div className="grid gap-4 lg:grid-cols-2"><div className="rounded-[24px] border border-border bg-bg3/70 p-4"><p className="text-sm font-semibold text-text">Code health heat map</p><div className="mt-4 h-[280px]"><ResponsiveContainer width="100%" height="100%"><BarChart data={results.tabs?.map?.heat_map || []}><CartesianGrid stroke="var(--border)" /><XAxis dataKey="file_path" stroke="var(--text2)" hide /><YAxis stroke="var(--text2)" /><Tooltip /><Bar dataKey="health_score" fill="var(--accent)" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer></div></div><div className="rounded-[24px] border border-border bg-bg3/70 p-4"><p className="text-sm font-semibold text-text">Duplication detector</p><div className="mt-4 space-y-3">{(results.tabs?.map?.duplicates || []).map((item) => <div key={item.id} className="rounded-2xl border border-border bg-bg2 px-4 py-3 text-sm text-text2">{item.summary}</div>)}{!(results.tabs?.map?.duplicates || []).length ? <p className="text-sm text-text2">No strong duplication pattern detected.</p> : null}</div></div></div></Panel></ScrollReveal> : null}
                {activeTab === "dependencies" ? (
                  <ScrollReveal delay={100}>
                    <Panel title="Dependencies" description="Package risks, contract gaps, and file-scoped follow-up guidance.">
                      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                        <div className="space-y-3">
                          <div className="flex flex-wrap gap-2 text-xs text-text2">
                            <span className="rounded-full border border-border bg-bg3 px-3 py-1.5">
                              Packages: {dependencyTab.dependency_count ?? 0}
                            </span>
                            <span className="rounded-full border border-border bg-bg3 px-3 py-1.5">
                              Manifests: {dependencyTab.manifest_count ?? 0}
                            </span>
                            <span className="rounded-full border border-border bg-bg3 px-3 py-1.5">
                              Targets: {results.source_overview?.target_count ?? results.file_count ?? 0}
                            </span>
                          </div>

                          {(dependencyTab.dependency_audit || []).map((item) => (
                            <div key={`${item.manifest_path}-${item.name}-${item.version}`} className="rounded-2xl border border-border bg-bg3/70 px-4 py-3">
                              <div className="flex flex-wrap items-center justify-between gap-3">
                                <p className="text-sm font-semibold text-text">
                                  {item.name} <span className="text-text2">{item.version}</span>
                                </p>
                                <span className="rounded-full border border-border bg-bg2 px-2.5 py-1 text-[11px] uppercase tracking-[0.14em] text-text3">
                                  {item.ecosystem}
                                </span>
                              </div>
                              <p className="mt-1 text-xs text-text3">{item.manifest_path}</p>
                              <p className="mt-2 text-sm text-text2">{item.fix_available}</p>
                              <p className="mt-2 text-xs text-text3">{item.severity} review priority • {item.section}</p>
                            </div>
                          ))}

                          {!(dependencyTab.dependency_audit || []).length ? (
                            <div className="rounded-2xl border border-border bg-bg3/70 p-4">
                              <p className="text-sm text-text2">No package manifest data was detected in this scan input.</p>
                              <p className="mt-2 text-xs text-text3">Upload or include files like package.json, requirements.txt, pyproject.toml, Cargo.toml, or go.mod for richer dependency analysis.</p>
                            </div>
                          ) : null}
                        </div>

                        <div className="space-y-4">
                          <div className="rounded-[24px] border border-border bg-bg3/70 p-4">
                            <p className="text-sm font-semibold text-text">Scanned targets</p>
                            <div className="mt-3 space-y-2">
                              {(dependencyTab.scanned_targets || results.source_overview?.targets || []).slice(0, 8).map((path) => (
                                <div key={path} className="rounded-xl border border-border bg-bg2 px-3 py-2 text-xs text-text2">
                                  {path}
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="rounded-[24px] border border-border bg-bg3/70 p-4">
                            <p className="text-sm font-semibold text-text">File findings & fixes</p>
                            <div className="mt-3 space-y-3">
                              {(dependencyTab.file_findings || []).map((item) => (
                                <div key={item.file_path} className="rounded-xl border border-border bg-bg2 px-3 py-3">
                                  <p className="text-sm font-semibold text-text">{item.file_path}</p>
                                  <p className="mt-1 text-xs text-text2">
                                    {item.issue_count} issues • {item.severities.join(", ")}
                                  </p>
                                  <p className="mt-2 text-sm text-text2">{item.top_issue}</p>
                                  <p className="mt-2 text-xs text-text3">Fix: {item.fix_summary}</p>
                                </div>
                              ))}
                              {!(dependencyTab.file_findings || []).length ? (
                                <p className="text-sm text-text2">No file-level guidance is available for this scan yet.</p>
                              ) : null}
                            </div>
                          </div>
                        </div>
                      </div>
                    </Panel>
                  </ScrollReveal>
                ) : null}
                {activeTab === "learn" ? (
                  <ScrollReveal delay={100}>
                    <Panel title="Learn" description="Guided lessons, quiz prompts, and interactive practice mode.">
                      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                        <div className="text-xs text-text2">
                          Source: {learnTab.source || "scan_generated"} | Updated: {formatDateTimeInIndia(learnTab.generated_at)}
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setRoastMode((current) => (current === "gentle" ? "brutal" : "gentle"))}
                            className="rounded-xl border border-border bg-bg3 px-4 py-2 text-sm font-semibold text-text2"
                          >
                            Code roast: {roastMode}
                          </button>
                          <button
                            type="button"
                            onClick={() => onQuickMessage(roastMode === "brutal" ? "Be brutal and roast this code." : "Roast this code gently but keep it useful.")}
                            className="rounded-xl border border-border bg-bg3 px-4 py-2 text-sm font-semibold text-text2"
                          >
                            Send roast to chat
                          </button>
                          <button type="button" onClick={onGenerateLearn} disabled={learnState.loading} className="inline-flex items-center gap-2 rounded-xl border border-[color:var(--accent)] bg-[linear-gradient(135deg,var(--accent),var(--accent-2))] px-4 py-2 text-sm font-semibold text-[#23150c] disabled:opacity-50"><Sparkles size={14} />{learnState.loading ? "Generating..." : "AI Generate"}</button>
                        </div>
                      </div>
                      {learnState.error ? <p className="mb-4 text-sm text-red">{learnState.error}</p> : null}
                      {!hasLearnContent ? (
                        <div className="mb-4 rounded-2xl border border-border bg-bg3/70 p-4">
                          <p className="text-sm text-text2">Learn content is empty for this scan right now. Click AI Generate to repopulate lessons and challenges.</p>
                        </div>
                      ) : null}
                      <div className="grid gap-4 lg:grid-cols-2">
                        <div className="rounded-[24px] border border-border bg-bg3/70 p-4">
                          <p className="text-sm font-semibold text-text">Micro lessons</p>
                          <div className="mt-4 space-y-3">
                            {(learnTab.micro_lessons || []).map((item) => (
                              <div key={`${item.finding_id || item.title}-lesson`} className="rounded-2xl border border-border bg-bg2 px-4 py-3">
                                <p className="text-sm font-semibold text-text">{item.title}</p>
                                <p className="mt-1 text-sm text-text2">{item.lesson}</p>
                                <p className="mt-2 text-xs text-text3">{item.story || item.fact}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="rounded-[24px] border border-border bg-bg3/70 p-4">
                          <p className="text-sm font-semibold text-text">Quiz & debate starters</p>
                          <div className="mt-4 space-y-3">
                            {(learnTab.quiz || []).map((item) => (
                              <div key={item.question} className="rounded-2xl border border-border bg-bg2 px-4 py-3">
                                <p className="text-sm font-semibold text-text">{item.question}</p>
                                <p className="mt-1 text-sm text-text2">{item.answer}</p>
                              </div>
                            ))}
                            {(learnTab.debate_starters || []).map((item) => (
                              <div key={`${item.finding_id}-debate`} className="rounded-2xl border border-border bg-bg2 px-4 py-3">
                                <p className="text-sm font-semibold text-text">Debate this finding</p>
                                <p className="mt-1 text-sm text-text2">{item.starter}</p>
                                <p className="mt-2 text-xs text-text3">{item.coach_reply}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="rounded-[24px] border border-border bg-bg3/70 p-4 lg:col-span-2">
                          <p className="text-sm font-semibold text-text">Fix it yourself</p>
                          <div className="mt-4 grid gap-3 md:grid-cols-2">
                            {(learnTab.fix_it_yourself || []).map((item) => (
                              <div key={`${item.finding_id}-fix`} className="rounded-2xl border border-border bg-bg2 px-4 py-3">
                                <p className="text-sm font-semibold text-text">{item.prompt}</p>
                                <p className="mt-1 text-sm text-text2">{item.hint}</p>
                                <p className="mt-2 text-xs text-text3">{item.success_criteria}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="rounded-[24px] border border-border bg-bg3/70 p-4 lg:col-span-2">
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-sm font-semibold text-text">Code Roast</p>
                            <span className="text-xs text-text3">Interactive tone switch</span>
                          </div>
                          <div className="mt-4 grid gap-3 md:grid-cols-2">
                            {(learnTab.code_roasts || []).map((item) => (
                              <div key={`${item.finding_id}-roast`} className="rounded-2xl border border-border bg-bg2 px-4 py-3">
                                <p className="text-sm font-semibold text-text">{item.title}</p>
                                <p className="mt-2 text-sm text-text2">{roastMode === "brutal" ? item.brutal : item.gentle}</p>
                                <p className="mt-2 text-xs text-text3">{item.teaching_point}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="rounded-[24px] border border-border bg-bg3/70 p-4 lg:col-span-2">
                          <p className="text-sm font-semibold text-text">Hacker Challenge Mode</p>
                          <div className="mt-4 grid gap-3 md:grid-cols-2">
                            {(learnTab.hacker_challenges || []).map((item) => {
                              const current = challengeState[item.finding_id] || {};
                              const result = current.evaluation;
                              return (
                                <div key={`${item.finding_id}-challenge`} className="rounded-2xl border border-border bg-bg2 px-4 py-3">
                                  <p className="text-sm font-semibold text-text">{item.title}</p>
                                  <p className="mt-1 text-sm text-text2">{item.prompt}</p>
                                  <p className="mt-2 text-xs text-text3">Hint: {item.hint}</p>
                                  <textarea
                                    value={current.answer || ""}
                                    onChange={(event) => setChallengeState((prev) => ({ ...prev, [item.finding_id]: { ...prev[item.finding_id], answer: event.target.value } }))}
                                    className="mt-3 min-h-[92px] w-full rounded-xl border border-border bg-bg3 px-3 py-3 text-sm text-text outline-none"
                                    placeholder="Type the payload or attack idea you would try first..."
                                    spellCheck="false"
                                  />
                                  <div className="mt-3 flex flex-wrap gap-2">
                                    <button
                                      type="button"
                                      onClick={() => setChallengeState((prev) => ({ ...prev, [item.finding_id]: { ...prev[item.finding_id], evaluation: evaluateChallenge(item.expected_keywords, prev[item.finding_id]?.answer || "") } }))}
                                      className="rounded-xl border border-border bg-bg3 px-3 py-2 text-sm text-text2"
                                    >
                                      Check answer
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => setChallengeState((prev) => ({ ...prev, [item.finding_id]: { ...prev[item.finding_id], reveal: !prev[item.finding_id]?.reveal } }))}
                                      className="rounded-xl border border-border bg-bg3 px-3 py-2 text-sm text-text2"
                                    >
                                      {current.reveal ? "Hide solution" : "Reveal solution"}
                                    </button>
                                  </div>
                                  {result ? <p className={`mt-3 text-sm ${result.isSuccess ? "text-green" : "text-yellow"}`}>{result.isSuccess ? "Nice attack idea. You hit at least one key exploit clue." : "Close, but try making the payload more explicit."}</p> : null}
                                  {current.reveal ? <p className="mt-2 text-xs text-text3">{item.solution}</p> : null}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                        <div className="rounded-[24px] border border-border bg-bg3/70 p-4 lg:col-span-2">
                          <p className="text-sm font-semibold text-text">Live Attack Simulator</p>
                          <div className="mt-4 grid gap-3 md:grid-cols-2">
                            {(learnTab.live_attack_labs || []).map((item) => {
                              const payload = labState.payloads[item.finding_id] ?? item.safe_default_payload ?? item.placeholder;
                              const output = labState.outputs[item.finding_id];
                              return (
                                <div key={`${item.finding_id}-lab`} className="rounded-2xl border border-border bg-bg2 px-4 py-3">
                                  <p className="text-sm font-semibold text-text">{item.title}</p>
                                  <p className="mt-1 text-xs uppercase tracking-[0.12em] text-text3">{item.label}</p>
                                  <input
                                    value={payload}
                                    onChange={(event) => setLabState((prev) => ({ ...prev, payloads: { ...prev.payloads, [item.finding_id]: event.target.value } }))}
                                    className="mt-3 w-full rounded-xl border border-border bg-bg3 px-3 py-3 text-sm text-text outline-none"
                                    placeholder={item.placeholder}
                                  />
                                  <div className="mt-3 flex flex-wrap gap-2">
                                    <button
                                      type="button"
                                      onClick={() => setLabState((prev) => ({ ...prev, outputs: { ...prev.outputs, [item.finding_id]: runAttackDemo({ title: item.title }, payload) } }))}
                                      className="rounded-xl border border-border bg-bg3 px-3 py-2 text-sm text-text2"
                                    >
                                      Run demo
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => setLabState((prev) => ({ ...prev, payloads: { ...prev.payloads, [item.finding_id]: item.safe_default_payload ?? item.placeholder } }))}
                                      className="rounded-xl border border-border bg-bg3 px-3 py-2 text-sm text-text2"
                                    >
                                      Use sample payload
                                    </button>
                                  </div>
                                  <p className="mt-3 text-xs text-text3">{item.expected_result}</p>
                                  {output ? (
                                    <div className="mt-3 rounded-xl border border-border bg-bg3 px-3 py-3">
                                      <p className="text-sm text-text">{output.verdict}</p>
                                      <div className="mt-2 space-y-1">
                                        {output.trace.map((step) => (
                                          <p key={step} className="text-xs text-text3">{step}</p>
                                        ))}
                                      </div>
                                      <p className="mt-2 text-xs text-text3">{item.impact}</p>
                                    </div>
                                  ) : null}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    </Panel>
                  </ScrollReveal>
                ) : null}

                <ScrollReveal delay={130}>
                  <Panel title="Findings" description="The detailed cards update to match the active workspace context.">
                    {resultsError ? <p className="text-sm text-red">{resultsError}</p> : null}
                    {resultsLoading && !results ? <div className="space-y-3"><FindingCardSkeleton /><FindingCardSkeleton /></div> : null}
                    <div className="space-y-3">
                      {!currentFindings.length && results ? (
                        <div className="rounded-2xl border border-border bg-bg3/70 p-4">
                          <p className="text-sm text-text2">No findings are visible in this view yet.</p>
                          <p className="mt-2 text-xs text-text3">Try another tab, or ask DevChat to summarize what the scan found in the selected files.</p>
                        </div>
                      ) : null}
                      {currentFindings.map((finding) => (
                        <div key={finding.id} className="space-y-2">
                          <IssueDetail finding={finding} beginnerMode={beginnerMode} />
                          <div className="flex items-center justify-end gap-2">
                            <button type="button" onClick={() => { onOpenFindingPanel(finding, "explain"); onQuickMessage(`Explain ${finding.title} step by step.`); }} className="rounded-xl border border-border bg-bg3 px-3 py-2 text-sm text-text2">Explain</button>
                            <button type="button" onClick={() => { onOpenFindingPanel(finding, "attack"); onRunFindingSimulation(finding); onQuickMessage(`Simulate how an attacker would exploit ${finding.title}.`); }} className="rounded-xl border border-border bg-bg3 px-3 py-2 text-sm text-text2">Simulate attack</button>
                            <FixThisButton loading={fixState.loadingFor === finding.id} disabled={Boolean(fixState.loadingFor && fixState.loadingFor !== finding.id)} onClick={() => onGenerateFix(finding)} />
                          </div>
                          {findingPanelState[finding.id]?.panel === "explain" ? (
                            <div className="rounded-2xl border border-border bg-bg2 px-4 py-4">
                              <p className="text-sm font-semibold text-text">Explanation</p>
                              <p className="mt-2 text-sm text-text2">{finding.explanation_card?.plain_english || finding.plain_english || finding.description}</p>
                              <p className="mt-2 text-sm text-text2">{finding.explanation_card?.why_it_matters}</p>
                              <p className="mt-2 text-xs text-text3">Next step: {finding.explanation_card?.next_step || finding.fix_suggestion}</p>
                            </div>
                          ) : null}
                          {findingPanelState[finding.id]?.panel === "attack" ? (
                            <div className="rounded-2xl border border-border bg-bg2 px-4 py-4">
                              <div className="flex flex-wrap items-center justify-between gap-3">
                                <p className="text-sm font-semibold text-text">Attack simulation</p>
                                <span className="text-xs text-text3">{finding.live_simulator?.label}</span>
                              </div>
                              <input
                                value={findingPanelState[finding.id]?.payload || finding.live_simulator?.safe_default_payload || finding.live_simulator?.placeholder || ""}
                                onChange={(event) => setFindingPanelState((prev) => ({ ...prev, [finding.id]: { ...prev[finding.id], payload: event.target.value, panel: "attack" } }))}
                                className="mt-3 w-full rounded-xl border border-border bg-bg3 px-3 py-3 text-sm text-text outline-none"
                                placeholder={finding.live_simulator?.placeholder}
                              />
                              <div className="mt-3 flex flex-wrap gap-2">
                                <button type="button" onClick={() => onRunFindingSimulation(finding)} className="rounded-xl border border-border bg-bg3 px-3 py-2 text-sm text-text2">Run payload</button>
                                <button
                                  type="button"
                                  onClick={() => setFindingPanelState((prev) => ({ ...prev, [finding.id]: { ...prev[finding.id], payload: finding.live_simulator?.safe_default_payload || finding.live_simulator?.placeholder, panel: "attack" } }))}
                                  className="rounded-xl border border-border bg-bg3 px-3 py-2 text-sm text-text2"
                                >
                                  Use sample payload
                                </button>
                              </div>
                              <div className="mt-3 space-y-2">
                                {(findingPanelState[finding.id]?.output?.trace || finding.attack_simulation?.steps || []).map((step) => (
                                  <p key={step} className="text-sm text-text2">{step}</p>
                                ))}
                              </div>
                              <p className="mt-2 text-sm text-text">{findingPanelState[finding.id]?.output?.verdict || finding.attack_simulation?.result}</p>
                              <p className="mt-2 text-xs text-text3">{finding.attack_simulation?.impact || finding.live_simulator?.impact}</p>
                            </div>
                          ) : null}
                          {fixState.errorFor[finding.id] ? <p className="text-xs text-yellow">{fixState.errorFor[finding.id]}</p> : null}
                          {fixState.byFinding[finding.id] ? <CodeDiffView before={fixState.byFinding[finding.id].before} after={fixState.byFinding[finding.id].after} language={fixState.byFinding[finding.id].language || results.input_language} metadata={fixState.byFinding[finding.id]} isEditable onAfterChange={(value) => onUpdateFixCode(finding.id, value)} onReset={() => onResetFixCode(finding.id)} /> : null}
                        </div>
                      ))}
                    </div>
                  </Panel>
                </ScrollReveal>

                <ScrollReveal delay={160}>
                  <Panel title="Export & Share" description="Download reports or create a public report link.">
                    <ExportShareBar scanId={scanId} />
                  </Panel>
                </ScrollReveal>
              </>
            ) : null}
          </section>
        </ErrorBoundary>

        {isDesktopChat ? <ChatBoundary><div className="xl:sticky xl:top-[84px]"><DevChatPanel title="Results DevChat" subtitle="Persistent scan-aware chat with smarter memory, repo search, and interactive roast mode." messages={messages} draft={draft} setDraft={setDraft} onSend={onSend} onClear={clearMessages} status={status} isStreaming={isStreaming} onQuickPrompt={onQuickMessage} quickPrompts={resultsQuickPrompts} minimalHeader /></div></ChatBoundary> : null}
      </div>

      {!isDesktopChat ? <div className={`fixed inset-0 z-40 ${chatOpen ? "" : "pointer-events-none"}`}><button type="button" onClick={() => setChatOpen(false)} className={`absolute inset-0 bg-black/30 transition-opacity duration-300 ${chatOpen ? "opacity-100" : "opacity-0"}`} aria-label="Close chat drawer" /><div className={`absolute right-0 top-0 h-full w-full max-w-[360px] p-3 transition-transform duration-300 ${chatOpen ? "translate-x-0" : "translate-x-full"}`}><ChatBoundary><div className="h-full overflow-auto"><DevChatPanel title="Results DevChat" subtitle="Persistent scan-aware chat with smarter memory, repo search, and interactive roast mode." messages={messages} draft={draft} setDraft={setDraft} onSend={onSend} onClear={clearMessages} onClose={() => setChatOpen(false)} status={status} isStreaming={isStreaming} onQuickPrompt={onQuickMessage} quickPrompts={resultsQuickPrompts} minimalHeader /></div></ChatBoundary></div></div> : null}
    </main>
  );
};

export default ResultsPage;
