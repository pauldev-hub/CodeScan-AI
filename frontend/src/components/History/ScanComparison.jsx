const formatScore = (value) => (value === null || value === undefined ? "n/a" : Number(value));

const ScanComparison = ({ items }) => {
  const latest = items?.[0];
  const previous = items?.[1];

  if (!latest || !previous) {
    return <p className="text-sm text-text2">Run at least two scans to compare trends.</p>;
  }

  const delta = (latest.health_score ?? 0) - (previous.health_score ?? 0);
  const deltaClass = delta > 0 ? "text-green" : delta < 0 ? "text-red" : "text-text2";

  return (
    <div className="grid gap-3 md:grid-cols-2">
      <div className="rounded-[10px] border border-border bg-bg3 p-3">
        <p className="text-xs uppercase tracking-[0.08em] text-text2">Latest</p>
        <p className="mt-2 text-sm font-semibold text-text">{latest.input_type?.toUpperCase()} scan</p>
        <p className="mt-1 text-xs text-text2">Score: {formatScore(latest.health_score)}</p>
        <p className="text-xs text-text2">Findings: {latest.total_findings ?? "n/a"}</p>
      </div>

      <div className="rounded-[10px] border border-border bg-bg3 p-3">
        <p className="text-xs uppercase tracking-[0.08em] text-text2">Previous</p>
        <p className="mt-2 text-sm font-semibold text-text">{previous.input_type?.toUpperCase()} scan</p>
        <p className="mt-1 text-xs text-text2">Score: {formatScore(previous.health_score)}</p>
        <p className="text-xs text-text2">Findings: {previous.total_findings ?? "n/a"}</p>
      </div>

      <div className="md:col-span-2 rounded-[10px] border border-border bg-bg2 p-3">
        <p className="text-xs uppercase tracking-[0.08em] text-text2">Score Delta</p>
        <p className={`mt-1 text-lg font-bold ${deltaClass}`}>{delta > 0 ? `+${delta}` : delta}</p>
      </div>
    </div>
  );
};

export default ScanComparison;
