import Badge from "../Common/Badge";

const beginnerSeverityLabel = {
  critical: "Urgent",
  high: "Important",
  medium: "Worth Fixing",
  low: "Minor",
};

const IssueDetail = ({ finding, beginnerMode }) => {
  const severity = (finding?.severity || "low").toLowerCase();
  const exploitRisk = Math.max(0, Math.min(100, Number(finding?.exploit_risk) || 0));
  const title = beginnerMode
    ? `${beginnerSeverityLabel[severity] || "Minor"}: ${finding.title}`
    : finding.title;
  const description = beginnerMode
    ? finding.plain_english || finding.description
    : finding.description || finding.plain_english;
  const fixPrefix = beginnerMode ? "How to fix it:" : "Fix suggestion:";

  return (
    <article className="rounded-lg border border-border bg-bg3 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-text">{title}</p>
          <p className="mt-1 text-xs text-text2">
            {finding.file_path}:{finding.line_number || "n/a"}
          </p>
        </div>
        <Badge severity={severity}>{beginnerMode ? beginnerSeverityLabel[severity] : severity}</Badge>
      </div>

      <p className="mt-2 text-sm text-text2">{description}</p>
      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between text-xs text-text2">
          <span>{beginnerMode ? "Exploit ease" : "Exploit risk"}</span>
          <span>{exploitRisk}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-bg2">
          <div
            className="h-full rounded-full bg-red transition-all duration-300"
            style={{ width: `${exploitRisk}%` }}
            aria-label={`Exploit risk ${exploitRisk} percent`}
          />
        </div>
      </div>
      <p className="mt-2 text-xs text-text2">{fixPrefix} {finding.fix_suggestion}</p>
    </article>
  );
};

export default IssueDetail;
