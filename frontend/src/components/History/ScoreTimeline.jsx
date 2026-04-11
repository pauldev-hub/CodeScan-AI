import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const formatDate = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return `${date.getMonth() + 1}/${date.getDate()}`;
};

const ScoreTimeline = ({ items }) => {
  const data = (items || [])
    .slice()
    .reverse()
    .map((scan, index) => ({
      date: scan.created_at,
      label: formatDate(scan.created_at),
      score: Number(scan.health_score ?? 0),
      findings: Number(scan.total_findings ?? 0),
      delta: index === 0 ? 0 : Number(scan.health_score ?? 0) - Number(items[items.length - index]?.health_score ?? 0),
    }));

  if (!data.length) {
    return <p className="text-sm text-text2">No timeline data yet.</p>;
  }

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 8 }}>
          <defs>
            <linearGradient id="scoreFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.45} />
              <stop offset="95%" stopColor="var(--accent)" stopOpacity={0.04} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border)" vertical={false} />
          <ReferenceLine y={80} stroke="var(--border-strong)" strokeDasharray="4 4" />
          <XAxis dataKey="label" stroke="var(--text2)" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} stroke="var(--text2)" tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 16, color: "var(--text)" }}
            formatter={(value, name) => [name === "score" ? `${value}/100` : value, name === "score" ? "Health score" : "Findings"]}
            labelFormatter={(_, payload) => (payload?.[0]?.payload ? `Scan ${payload[0].payload.label}` : "")}
          />
          <Area type="monotone" dataKey="score" stroke="var(--accent)" strokeWidth={3} fill="url(#scoreFill)" />
          <Area type="monotone" dataKey="findings" stroke="var(--red)" strokeOpacity={0.7} fillOpacity={0} strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ScoreTimeline;
