import clsx from "clsx";

const palette = {
  critical: "bg-red text-white",
  high: "bg-yellow text-white",
  medium: "bg-purple text-white",
  low: "bg-green text-white",
};

const Badge = ({ severity = "low", children, className }) => (
  <span
    className={clsx(
      "inline-flex items-center rounded-full px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-[0.08em]",
      palette[severity] || palette.low,
      className
    )}
  >
    {children || severity}
  </span>
);

export default Badge;
