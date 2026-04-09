import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

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
    .map((scan) => ({
      date: scan.created_at,
      score: Number(scan.health_score ?? 0),
    }));

  if (!data.length) {
    return <p className="text-sm text-text2">No timeline data yet.</p>;
  }

  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: -24, bottom: 8 }}>
          <XAxis dataKey="date" tickFormatter={formatDate} stroke="var(--text2)" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} stroke="var(--text2)" tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              background: "var(--bg2)",
              border: "1px solid var(--border)",
              borderRadius: 10,
              color: "var(--text)",
            }}
            labelFormatter={(label) => `Date: ${formatDate(label)}`}
          />
          <Line type="monotone" dataKey="score" stroke="var(--accent)" strokeWidth={2} dot={{ r: 2 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ScoreTimeline;
