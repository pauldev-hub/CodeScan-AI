import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
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
    return "Scan input is invalid. Check the URL, code snippet, or files and try again.";
  }
  if (apiError?.status === 503) {
    return "Scan worker is temporarily unavailable. Retry in a few moments.";
  }
  return apiError?.message || "Unable to submit scan";
};

const getResultsRoute = (scanId) => APP_ROUTES.results.replace(":scanId", scanId);

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
    <main className="space-y-4">
      <Card>
        <h1 className="text-xl font-bold">New Scan</h1>
        <p className="mt-1 text-sm text-text2">Choose an input mode to start your security analysis.</p>
        <div className="mt-4">
          <Tabs tabs={tabs} activeTab={mode} onChange={setMode} />
        </div>

        <div className="mt-4 space-y-3">
          {mode === "url" ? (
            <input
              className="w-full rounded-lg border border-border bg-bg3 px-3 py-2"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
            />
          ) : null}

          {mode === "paste" ? (
            <>
              <div className="grid gap-2 sm:grid-cols-[1fr_220px]">
                <textarea
                  className="min-h-40 w-full rounded-lg border border-border bg-bg3 px-3 py-2 font-mono text-sm"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Paste code here..."
                />
                <select
                  className="h-10 rounded-lg border border-border bg-bg3 px-3 py-2 text-sm"
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
            </>
          ) : null}

          {mode === "upload" ? (
            <div className="space-y-2">
              <input
                className="w-full rounded-lg border border-border bg-bg3 px-3 py-2 text-sm"
                type="file"
                multiple
                onChange={(event) => setFiles(Array.from(event.target.files || []))}
              />
              <p className="text-xs text-text2">Selected files: {files.length}</p>
            </div>
          ) : null}

          {error ? <p className="text-sm text-red">{error}</p> : null}
          <Button isLoading={loading} onClick={submit}>
            Start Scan
          </Button>
          <p className="text-xs text-text2">
            If you hit rate limits, wait for your hourly quota window to reset before retrying.
          </p>
        </div>
      </Card>
    </main>
  );
};

export default ScanPage;
