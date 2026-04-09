import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { copyToClipboard } from "../../utils/clipboard";

const CopyButton = ({ value }) => {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await copyToClipboard(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };

  return (
    <button
      type="button"
      onClick={onCopy}
      className="inline-flex items-center gap-1 rounded-md border border-border bg-bg3 px-2 py-1 text-xs text-text2 transition-colors hover:bg-bg2"
      aria-label={copied ? "Copied" : "Copy to clipboard"}
    >
      {copied ? <Check size={14} className="text-green" /> : <Copy size={14} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
};

export default CopyButton;
