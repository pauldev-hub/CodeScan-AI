import { Download, Share2 } from "lucide-react";
import { useState } from "react";

import Button from "../Common/Button";
import { createShareLink } from "../../services/reportService";
import { downloadScanExport } from "../../services/exportService";
import { copyToClipboard } from "../../utils/clipboard";

const formatButtons = [
  { label: "PDF", value: "pdf" },
  { label: "JSON", value: "json" },
  { label: "CSV", value: "csv" },
  { label: "MD", value: "md" },
];

const toPublicShareRoute = (rawPath) => {
  const shareId = (rawPath || "").split("/").pop();
  return shareId ? `${window.location.origin}/report/shared/${shareId}` : "";
};

const ExportShareBar = ({ scanId }) => {
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  const onExport = async (format) => {
    setBusy(`export:${format}`);
    setMessage("");
    try {
      await downloadScanExport(scanId, format);
      setMessage(`${format.toUpperCase()} export downloaded.`);
    } catch (error) {
      setMessage(error?.message || "Unable to export report.");
    } finally {
      setBusy("");
    }
  };

  const onShare = async () => {
    setBusy("share");
    setMessage("");
    try {
      const payload = await createShareLink(scanId);
      const shareLink = toPublicShareRoute(payload?.share_link);
      if (!shareLink) {
        throw new Error("Unable to build share link.");
      }
      await copyToClipboard(shareLink);
      setMessage("Share link copied to clipboard.");
    } catch (error) {
      setMessage(error?.message || "Unable to create share link.");
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="rounded-[10px] border border-border bg-bg2 p-3">
      <div className="flex flex-wrap items-center gap-2">
        {formatButtons.map((item) => (
          <Button
            key={item.value}
            size="sm"
            variant="ghost"
            onClick={() => onExport(item.value)}
            isLoading={busy === `export:${item.value}`}
            disabled={Boolean(busy)}
          >
            <Download size={14} />
            {item.label}
          </Button>
        ))}

        <Button size="sm" onClick={onShare} isLoading={busy === "share"} disabled={Boolean(busy)} className="ml-auto">
          <Share2 size={14} />
          Share Report
        </Button>
      </div>

      {message ? <p className="mt-2 text-xs text-text2">{message}</p> : null}
    </div>
  );
};

export default ExportShareBar;
