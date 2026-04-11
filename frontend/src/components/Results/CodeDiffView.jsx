import CodeBlock from "../Common/CodeBlock";

const toLines = (text) => (text || "").split("\n");

const buildRows = (before, after) => {
  const beforeLines = toLines(before);
  const afterLines = toLines(after);
  const max = Math.max(beforeLines.length, afterLines.length);
  const rows = [];
  let added = 0;
  let removed = 0;
  let changed = 0;

  for (let index = 0; index < max; index += 1) {
    const beforeLine = beforeLines[index];
    const afterLine = afterLines[index];
    let type = "same";
    if (beforeLine === undefined && afterLine !== undefined) {
      type = "added";
      added += 1;
    } else if (beforeLine !== undefined && afterLine === undefined) {
      type = "removed";
      removed += 1;
    } else if (beforeLine !== afterLine) {
      type = "changed";
      changed += 1;
    }
    rows.push({ index, beforeLine, afterLine, type });
  }

  return { rows, added, removed, changed };
};

const CodeDiffView = ({
  before = "",
  after = "",
  language = "javascript",
  onAfterChange,
  isEditable = false,
  metadata = null,
  onReset,
}) => {
  const beforeLines = toLines(before);
  const afterLines = toLines(after);
  const { rows, added, removed, changed } = buildRows(before, after);

  return (
    <div className="space-y-3 rounded-lg border border-border bg-bg2 p-3">
      <p className="text-sm font-semibold text-text">Before / After Diff Preview</p>

      {metadata?.change_summary?.length ? (
        <div className="rounded-md border border-border bg-bg3 p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-text2">Fix plan</p>
          <div className="mt-2 space-y-1">
            {metadata.change_summary.map((item) => (
              <p key={item} className="text-sm text-text2">{item}</p>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid gap-3 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-xs uppercase tracking-[0.08em] text-text2">Before</p>
          <CodeBlock code={before} language={language} />
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between gap-3">
            <p className="text-xs uppercase tracking-[0.08em] text-text2">After</p>
            {isEditable ? (
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-text3">Edit code</span>
                {onReset ? (
                  <button type="button" onClick={onReset} className="rounded-lg border border-border bg-bg3 px-2 py-1 text-[11px] text-text2">
                    Reset
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
          {isEditable ? (
            <textarea
              value={after}
              onChange={(event) => onAfterChange?.(event.target.value)}
              className="min-h-[220px] w-full rounded-lg border border-border bg-bg3 px-3 py-3 font-mono text-xs text-text outline-none"
              spellCheck="false"
            />
          ) : (
            <CodeBlock code={after} language={language} />
          )}
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_240px]">
        <div className="overflow-hidden rounded-md border border-border bg-bg3">
          <div className="border-b border-border px-3 py-2">
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-text2">Changed lines</p>
          </div>
          <div className="max-h-[240px] overflow-auto">
            {rows.filter((row) => row.type !== "same").length ? rows.filter((row) => row.type !== "same").map((row) => (
              <div
                key={`${row.index}-${row.type}`}
                className={`grid grid-cols-[28px_minmax(0,1fr)] gap-2 px-3 py-2 font-mono text-xs ${
                  row.type === "added"
                    ? "bg-green/10 text-green"
                    : row.type === "removed"
                      ? "bg-red/10 text-red"
                      : "bg-yellow/10 text-yellow"
                }`}
              >
                <span>{row.type === "added" ? "+" : row.type === "removed" ? "-" : "~"}</span>
                <span className="break-all">{row.afterLine ?? row.beforeLine ?? ""}</span>
              </div>
            )) : <p className="px-3 py-3 text-sm text-text2">No line-level changes yet.</p>}
          </div>
        </div>
        <div className="rounded-md border border-border bg-bg3 p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-text2">Diff stats</p>
          <div className="mt-2 space-y-1 text-sm text-text2">
            <p>Before lines: {beforeLines.length}</p>
            <p>After lines: {afterLines.length}</p>
            <p>Added: {metadata?.diff_stats?.added_lines ?? added}</p>
            <p>Removed: {metadata?.diff_stats?.removed_lines ?? removed}</p>
            <p>Changed: {metadata?.diff_stats?.changed_lines ?? changed}</p>
          </div>
          {metadata?.edit_hints?.length ? (
            <div className="mt-3 space-y-1 border-t border-border pt-3">
              {metadata.edit_hints.map((hint) => (
                <p key={hint} className="text-xs text-text3">{hint}</p>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default CodeDiffView;
