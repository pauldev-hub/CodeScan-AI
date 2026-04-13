import { useMemo, useState } from "react";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  FileCode2,
  Folder,
  FolderOpen,
  Github,
  LoaderCircle,
  ScanSearch,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
import Tabs from "../components/Common/Tabs";
import {
  previewGithubRepository,
  submitScanByPaste,
  submitScanByUpload,
  submitScanByUrl,
} from "../services/scanService";
import { APP_ROUTES } from "../utils/constants";
import { detectLanguageFromCode, detectLanguageFromFilename } from "../utils/language";

const MAX_UPLOAD_FILES = 18;
const SCAN_FACTS = [
  {
    title: "Dependency clues",
    body: "Manifests such as package.json, requirements.txt, pyproject.toml, Cargo.toml, and go.mod now help the scanner build richer dependency insights.",
  },
  {
    title: "Smarter DevChat",
    body: "DevChat can now lean on scan context for repo-style code search, roast mode, and memory-aware follow-ups.",
  },
  {
    title: "Selective repo scans",
    body: "For GitHub repos you can pick folders or files first, then scan only those paths instead of the entire repository.",
  },
  {
    title: "Language detection",
    body: "Paste code without choosing a language first. The workspace now infers the dominant language automatically.",
  },
  {
    title: "Better learning mode",
    body: "Learn mode can fall back to seeded micro-lessons, hacker challenges, and roast content when AI generation is sparse.",
  },
];

const isTimeoutError = (apiError) => {
  const rawCode = apiError?.raw?.code;
  const message = `${apiError?.message || ""}`.toLowerCase();
  return rawCode === "ECONNABORTED" || message.includes("timeout");
};

const mapScanSubmitError = (apiError) => {
  if (isTimeoutError(apiError)) {
    return "Scan request timed out. The server may be queueing work; retry in a few seconds, or verify backend/worker services are running.";
  }
  if (!apiError?.status) {
    return "Cannot reach the scan API. Check that frontend API URL and backend server are running.";
  }
  if (apiError?.status === 429) {
    return "Scan limit reached: 10 scans per hour. Wait for your hourly window to reset, then retry.";
  }
  if (apiError?.status === 400) {
    const message = apiError?.message || "";
    if (/github/i.test(message)) {
      return "The repository URL is invalid. Paste a public GitHub repository URL like https://github.com/owner/repo.";
    }
    if (/code is required/i.test(message)) {
      return "Paste some code into the editor before starting a scan.";
    }
    if (/unsupported file type/i.test(message)) {
      return "One or more uploaded files are not supported. Use code files such as .js, .ts, .py, .java, .go, or .rs.";
    }
    if (/file too large/i.test(message) || /total upload size/i.test(message)) {
      return "Your upload is too large for the current limits. Remove the biggest files and retry.";
    }
    return message || "Scan input is invalid. Check the URL, code snippet, or files and try again.";
  }
  if (apiError?.status === 503) {
    return "Scan worker is temporarily unavailable. Retry in a few moments.";
  }
  return apiError?.message || "Unable to submit scan";
};

const getResultsRoute = (scanId) => APP_ROUTES.results.replace(":scanId", scanId);

const getLineNumbers = (code) =>
  Array.from({ length: Math.max(16, (code || "").split("\n").length) }, (_, index) => index + 1).join("\n");

const pickWorkspaceFacts = () => {
  const seed = new Date().getDate();
  return [...SCAN_FACTS]
    .sort((left, right) => ((left.title.length + seed) % 7) - ((right.title.length + seed) % 7))
    .slice(0, 3);
};

const RepoTreeNode = ({ node, depth = 0, selectedPaths, onToggle }) => {
  const isDirectory = node.type === "dir";
  const selected = selectedPaths.includes(node.path);
  const supported = node.is_supported !== false;

  return (
    <div className="space-y-1">
      <button
        type="button"
        onClick={() => supported && onToggle(node.path)}
        className={`flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-left transition-colors ${
          selected ? "bg-[color:var(--accent-glow)] text-text" : "hover:bg-bg3/70"
        } ${supported ? "" : "opacity-45"}`}
        style={{ paddingLeft: `${14 + depth * 18}px` }}
      >
        <span
          className={`inline-flex h-5 w-5 items-center justify-center rounded-md border ${
            selected ? "border-[color:var(--accent)] bg-[color:var(--accent)] text-[#20120b]" : "border-border bg-bg3 text-text3"
          }`}
        >
          {selected ? <Check size={12} /> : null}
        </span>
        {isDirectory ? <ChevronRight size={14} className="text-text3" /> : <span className="w-[14px]" />}
        {isDirectory ? (
          <Folder size={15} className={selected ? "text-accent" : "text-text3"} />
        ) : (
          <FileCode2 size={15} className={supported ? "text-accent" : "text-text3"} />
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{node.name}</p>
          <p className="truncate text-[11px] text-text3">
            {isDirectory ? "Folder selection scans everything inside it." : node.is_manifest ? "Dependency manifest" : node.path}
          </p>
        </div>
      </button>

      {Array.isArray(node.children) && node.children.length ? (
        <div className="space-y-1">
          {node.children.map((child) => (
            <RepoTreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPaths={selectedPaths}
              onToggle={onToggle}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
};

const ScanPage = () => {
  const [mode, setMode] = useState("url");
  const [githubUrl, setGithubUrl] = useState("");
  const [code, setCode] = useState("");
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [previewState, setPreviewState] = useState({ loading: false, error: "", data: null });
  const [selectedPaths, setSelectedPaths] = useState([]);
  const navigate = useNavigate();

  const tabs = useMemo(
    () => [
      { value: "url", label: "GitHub URL" },
      { value: "paste", label: "Paste Code" },
      { value: "upload", label: "Upload Files" },
    ],
    []
  );

  const workspaceFacts = useMemo(() => pickWorkspaceFacts(), []);
  const detectedPasteLanguage = useMemo(() => detectLanguageFromCode(code), [code]);
  const detectedUploadLanguage = useMemo(() => {
    const candidates = files.map((file) => detectLanguageFromFilename(file.name)).filter((item) => item !== "Text");
    return candidates[0] || "Text";
  }, [files]);

  const repoPreview = previewState.data;

  const validateScanInput = () => {
    if (mode === "url") {
      const valid = /^https?:\/\/(www\.)?github\.com\/.+\/.+/i.test(githubUrl.trim());
      if (!valid) {
        return "Enter a valid GitHub repository URL.";
      }
    }

    if (mode === "paste" && !code.trim()) {
      return "Paste code before starting a scan.";
    }

    if (mode === "upload") {
      if (!files.length) {
        return "Choose at least one file to upload.";
      }
      if (files.length > MAX_UPLOAD_FILES) {
        return `You can upload up to ${MAX_UPLOAD_FILES} files per scan.`;
      }
    }

    return "";
  };

  const loadRepoPreview = async () => {
    if (!githubUrl.trim()) {
      setError("Paste a GitHub URL first.");
      return;
    }

    setError("");
    setPreviewState({ loading: true, error: "", data: null });
    try {
      const data = await previewGithubRepository(githubUrl.trim());
      setPreviewState({ loading: false, error: "", data });
      setSelectedPaths([]);
    } catch (apiError) {
      setPreviewState({
        loading: false,
        error: mapScanSubmitError(apiError),
        data: null,
      });
    }
  };

  const submit = async (scanEntireRepo = false) => {
    setError("");
    const validationError = validateScanInput();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    try {
      let payload;
      if (mode === "url") {
        payload = await submitScanByUrl(githubUrl.trim(), {
          selectedPaths,
          scanEntireRepo: scanEntireRepo || !selectedPaths.length,
        });
      } else if (mode === "paste") {
        payload = await submitScanByPaste(code);
      } else {
        payload = await submitScanByUpload(files);
      }

      navigate(getResultsRoute(payload.scan_id), {
        state: {
          queuedAt: Date.now(),
          sourceMode: mode,
          justSubmitted: true,
        },
      });
    } catch (apiError) {
      setError(mapScanSubmitError(apiError));
    } finally {
      setLoading(false);
    }
  };

  const togglePath = (path) => {
    setSelectedPaths((current) =>
      current.includes(path) ? current.filter((item) => item !== path) : [...current, path]
    );
  };

  return (
    <main className="space-y-5">
      <ScrollReveal className="grid gap-5 xl:grid-cols-[1.24fr_0.76fr]">
        <section className="codescan-editor-surface overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3 md:px-5">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">Scan workspace</p>
              <h1 className="mt-2 text-2xl font-bold text-text md:text-3xl">Open a new review session</h1>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-text2">
                Choose a repo, paste a snippet, or upload a focused set of files. The scanner now supports selective GitHub path scans and automatic language detection.
              </p>
            </div>
            <span className="rounded-full border border-border bg-bg3 px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-text2">
              live review
            </span>
          </div>

          <div className="px-4 py-4 md:px-5">
            <Tabs tabs={tabs} activeTab={mode} onChange={setMode} />

            <div className="mt-4 space-y-4">
              {mode === "url" ? (
                <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                  <div className="rounded-[24px] border border-border bg-bg3/60 p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-text">
                      <Github size={16} className="text-accent" />
                      Repository source
                    </div>
                    <input
                      className="mt-4 w-full rounded-2xl border border-border bg-bg2 px-4 py-3 text-sm"
                      value={githubUrl}
                      onChange={(event) => setGithubUrl(event.target.value)}
                      placeholder="https://github.com/owner/repo"
                    />
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button variant="ghost" size="sm" onClick={loadRepoPreview} disabled={previewState.loading || loading} isLoading={previewState.loading}>
                        {previewState.loading ? <LoaderCircle size={14} className="animate-spin" /> : <ScanSearch size={14} />}
                        Load files
                      </Button>
                      <Button size="sm" onClick={() => submit(true)} disabled={loading || previewState.loading} isLoading={loading}>
                        Scan entire repo
                        <ArrowUpRight size={14} />
                      </Button>
                    </div>
                    <p className="mt-3 text-xs text-text2">
                      Load the repo tree to choose folders/files like GitHub, or skip straight to a full-repo scan.
                    </p>
                    {repoPreview?.summary ? (
                      <div className="mt-4 rounded-2xl border border-border bg-bg2/70 p-3 text-xs text-text2">
                        <p>Supported files: {repoPreview.summary.supported_file_count}</p>
                        <p>Dependency manifests: {repoPreview.summary.manifest_count}</p>
                        <p className="mt-2">
                          Top file types:{" "}
                          {(repoPreview.summary.top_extensions || [])
                            .map((item) => `${item.extension} (${item.count})`)
                            .join(", ") || "n/a"}
                        </p>
                      </div>
                    ) : null}
                    {previewState.error ? <p className="mt-4 text-sm text-red">{previewState.error}</p> : null}
                  </div>

                  <div className="rounded-[24px] border border-border bg-bg3/60 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-text">Choose what to scan</p>
                        <p className="mt-1 text-xs text-text2">Select a file for a focused scan or a folder to include everything inside it.</p>
                      </div>
                      <span className="rounded-full border border-border bg-bg2 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-text3">
                        {selectedPaths.length ? `${selectedPaths.length} selected` : "entire repo by default"}
                      </span>
                    </div>

                    <div className="mt-4 max-h-[520px] overflow-auto rounded-2xl border border-border bg-[color:var(--panel-strong)] p-2">
                      {previewState.loading ? (
                        <div className="space-y-3 p-3">
                          {Array.from({ length: 6 }, (_, index) => (
                            <div key={`repo-skeleton-${index}`} className="h-11 animate-pulse rounded-2xl bg-bg3" />
                          ))}
                        </div>
                      ) : null}

                      {!previewState.loading && !repoPreview ? (
                        <div className="p-4 text-sm text-text2">
                          Load a repository to see a file/folder tree here before you scan.
                        </div>
                      ) : null}

                      {!previewState.loading && repoPreview?.tree?.length
                        ? repoPreview.tree.map((node) => (
                            <RepoTreeNode
                              key={node.path}
                              node={node}
                              selectedPaths={selectedPaths}
                              onToggle={togglePath}
                            />
                          ))
                        : null}
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button onClick={() => submit(false)} disabled={loading || previewState.loading} isLoading={loading}>
                        Start selected scan
                        <ArrowUpRight size={16} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedPaths([])}
                        disabled={!selectedPaths.length}
                      >
                        Clear selection
                      </Button>
                    </div>
                    {loading ? <p className="mt-3 text-xs text-text2">Starting the selected scan and opening the results workspace...</p> : null}
                  </div>
                </div>
              ) : null}

              {mode === "paste" ? (
                <div className="codescan-editor-surface mt-1 overflow-hidden">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
                    <div className="flex items-center gap-2 text-sm font-semibold text-text">
                      <FileCode2 size={16} className="text-accent" />
                      Paste code
                    </div>
                    <div className="rounded-full border border-border bg-bg3 px-3 py-2 text-xs text-text2">
                      Auto-detected language: <span className="font-semibold text-text">{detectedPasteLanguage}</span>
                    </div>
                  </div>
                  <div className="codescan-editor-grid">
                    <pre className="codescan-editor-gutter">{getLineNumbers(code)}</pre>
                    <textarea
                      className="codescan-editor-textarea"
                      value={code}
                      onChange={(event) => setCode(event.target.value)}
                      placeholder="Paste your code here. The scanner will detect the language, review the snippet, and explain the risk in plain English."
                      spellCheck="false"
                    />
                  </div>
                  <div className="codescan-editor-meta flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-xs text-text2">
                    <span>Language: {detectedPasteLanguage}</span>
                    <span>Characters: {code.length} • long snippets are auto-chunked for analysis</span>
                  </div>
                </div>
              ) : null}

              {mode === "upload" ? (
                <div className="rounded-[24px] border border-border bg-bg3/60 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-sm font-semibold text-text">
                      <FolderOpen size={16} className="text-accent" />
                      Upload source files
                    </div>
                    <span className="rounded-full border border-border bg-bg2 px-3 py-2 text-xs text-text2">
                      Detected: <span className="font-semibold text-text">{detectedUploadLanguage}</span>
                    </span>
                  </div>
                  <input
                    className="mt-4 w-full rounded-2xl border border-dashed border-border bg-bg2 px-4 py-10 text-sm"
                    type="file"
                    multiple
                    onChange={(event) => setFiles(Array.from(event.target.files || []))}
                  />
                  <div className="mt-4 grid gap-2 md:grid-cols-2">
                    {files.slice(0, 8).map((file) => (
                      <div key={`${file.name}-${file.size}`} className="rounded-2xl border border-border bg-bg2 px-4 py-3">
                        <p className="truncate text-sm font-medium text-text">{file.name}</p>
                        <p className="mt-1 text-xs text-text2">
                          {detectLanguageFromFilename(file.name)} • {Math.max(1, Math.round(file.size / 1024))} KB
                        </p>
                      </div>
                    ))}
                  </div>
                  <p className="mt-3 text-xs text-text2">Selected files: {files.length}</p>
                </div>
              ) : null}
            </div>

            {error ? <p className="mt-4 text-sm text-red">{error}</p> : null}

            {mode !== "url" ? (
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <Button isLoading={loading} onClick={() => submit(false)} disabled={loading}>
                  Start Scan
                  <ArrowUpRight size={16} />
                </Button>
                <p className="text-xs text-text2">
                  If you hit rate limits, wait for your hourly quota window to reset before retrying.
                </p>
              </div>
            ) : null}
          </div>
        </section>

        <div className="grid gap-3 self-start">
          <Card className="overflow-hidden bg-[linear-gradient(160deg,rgba(214,161,108,0.18),rgba(255,255,255,0.02))]">
            <div className="flex items-center gap-2 text-accent">
              <ShieldCheck size={16} />
              <span className="text-[11px] uppercase tracking-[0.16em]">What you get</span>
            </div>
            <p className="mt-4 text-sm leading-7 text-text2">
              Severity breakdown, dependency hints, file-scoped diagnostics, plain-English explanations, and a more capable DevChat tied to the scan context.
            </p>
          </Card>

          <Card>
            <div className="flex items-center gap-2 text-text3">
              <Sparkles size={16} />
              <span className="text-[11px] uppercase tracking-[0.16em]">Workspace pulse</span>
            </div>
            <div className="mt-4 space-y-3">
              {workspaceFacts.map((fact) => (
                <div key={fact.title} className="rounded-[20px] border border-border bg-bg3/70 p-4">
                  <p className="text-sm font-semibold text-text">{fact.title}</p>
                  <p className="mt-2 text-sm leading-6 text-text2">{fact.body}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card className="bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01))]">
            <div className="flex items-center gap-2 text-text3">
              <Sparkles size={16} />
              <span className="text-[11px] uppercase tracking-[0.16em]">Quick suggestions</span>
            </div>
            <div className="mt-4 space-y-2 text-sm text-text2">
              <p>Try scanning only `src/auth` or `api/routes` first when a repo is large.</p>
              <p>Upload a manifest with the code if you want better dependency cues.</p>
              <p>Paste just one risky function when you want fast fix previews.</p>
            </div>
          </Card>
        </div>
      </ScrollReveal>
    </main>
  );
};

export default ScanPage;
