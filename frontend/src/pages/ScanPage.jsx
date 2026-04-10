import { useMemo, useState } from "react";
import { ArrowUpRight, FileCode2, FolderOpen, Github, ShieldCheck, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
import Tabs from "../components/Common/Tabs";
import { submitScanByPaste, submitScanByUpload, submitScanByUrl } from "../services/scanService";
import { APP_ROUTES } from "../utils/constants";

const MAX_UPLOAD_FILES = 12;

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
      return "Paste some code into the editor before starting the scan.";
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

const ScanPage = () => {
  const [mode, setMode] = useState("url");
  const [githubUrl, setGithubUrl] = useState("");
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("javascript");
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const tabs = useMemo(
    () => [
      { value: "url", label: "GitHub URL" },
      { value: "paste", label: "Paste Code" },
      { value: "upload", label: "Upload Files" },
    ],
    []
  );

  const validateScanInput = () => {
    if (mode === "url") {
      const valid = /^https?:\/\/(www\.)?github\.com\/.+\/.+/i.test(githubUrl.trim());
      if (!valid) {
        return "Enter a valid GitHub repository URL.";
      }
    }

    if (mode === "paste") {
      if (!code.trim()) {
        return "Paste code before starting a scan.";
      }
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

  const submit = async () => {
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
        payload = await submitScanByUrl(githubUrl.trim());
      } else if (mode === "paste") {
        payload = await submitScanByPaste(code, language);
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

  return (
    <main className="space-y-5">
      <ScrollReveal className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="codescan-editor-surface">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3 md:px-5">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">Scan workspace</p>
              <h1 className="mt-2 text-2xl font-bold text-text md:text-3xl">Open a new review session</h1>
            </div>
            <span className="rounded-full border border-border bg-bg3 px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-text2">
              editor mode
            </span>
          </div>

          <div className="px-4 py-4 md:px-5">
            <Tabs tabs={tabs} activeTab={mode} onChange={setMode} />

            <div className="mt-4">
              {mode === "url" ? (
                <div className="rounded-[24px] border border-border bg-bg3/60 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-text">
                    <Github size={16} className="text-accent" />
                    Repository source
                  </div>
                  <input
                    className="mt-4 w-full rounded-2xl border border-border bg-bg2 px-4 py-3 text-sm"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/owner/repo"
                  />
                  <p className="mt-3 text-xs text-text2">Public GitHub repositories work best for the current scanner.</p>
                </div>
              ) : null}

              {mode === "paste" ? (
                <div className="codescan-editor-surface mt-1">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
                    <div className="flex items-center gap-2 text-sm font-semibold text-text">
                      <FileCode2 size={16} className="text-accent" />
                      Paste code
                    </div>
                    <select
                      className="h-10 rounded-xl border border-border bg-bg3 px-3 py-2 text-sm"
                      value={language}
                      onChange={(event) => setLanguage(event.target.value)}
                    >
                      <option value="javascript">JavaScript</option>
                      <option value="python">Python</option>
                      <option value="typescript">TypeScript</option>
                      <option value="java">Java</option>
                      <option value="go">Go</option>
                    </select>
                  </div>
                  <div className="codescan-editor-grid">
                    <pre className="codescan-editor-gutter">{getLineNumbers(code)}</pre>
                    <textarea
                      className="codescan-editor-textarea"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      placeholder="Paste your code here. The scanner will review the current snippet and explain the risk in plain English."
                      spellCheck="false"
                    />
                  </div>
                  <div className="codescan-editor-meta flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-xs text-text2">
                    <span>Language: {language}</span>
                    <span>Characters: {code.length}</span>
                  </div>
                </div>
              ) : null}

              {mode === "upload" ? (
                <div className="rounded-[24px] border border-border bg-bg3/60 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-text">
                    <FolderOpen size={16} className="text-accent" />
                    Upload source files
                  </div>
                  <input
                    className="mt-4 w-full rounded-2xl border border-dashed border-border bg-bg2 px-4 py-10 text-sm"
                    type="file"
                    multiple
                    onChange={(event) => setFiles(Array.from(event.target.files || []))}
                  />
                  <p className="mt-3 text-xs text-text2">Selected files: {files.length}</p>
                </div>
              ) : null}
            </div>

            {error ? <p className="mt-4 text-sm text-red">{error}</p> : null}

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Button isLoading={loading} onClick={submit} disabled={loading}>
                Start Scan
                <ArrowUpRight size={16} />
              </Button>
              <p className="text-xs text-text2">
                If you hit rate limits, wait for your hourly quota window to reset before retrying.
              </p>
            </div>
          </div>
        </section>

        <Card className="grid gap-3 self-start">
          <div className="rounded-[20px] border border-border bg-bg3/70 p-4">
            <div className="flex items-center gap-2 text-text3">
              <ShieldCheck size={16} />
              <span className="text-[11px] uppercase tracking-[0.16em]">What you get</span>
            </div>
            <p className="mt-3 text-sm leading-7 text-text2">Severity breakdown, health score, plain-English explanations, and an AI chat panel tied to the scan context.</p>
          </div>
          <div className="rounded-[20px] border border-border bg-bg3/70 p-4">
            <div className="flex items-center gap-2 text-text3">
              <Sparkles size={16} />
              <span className="text-[11px] uppercase tracking-[0.16em]">Review style</span>
            </div>
            <p className="mt-3 text-sm leading-7 text-text2">The workspace is tuned for quick triage first, then deeper learning and follow-up fixes.</p>
          </div>
        </Card>
      </ScrollReveal>
    </main>
  );
};

export default ScanPage;
