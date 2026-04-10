const BeginnerModeToggle = ({ enabled, onToggle }) => (
  <button
    type="button"
    onClick={onToggle}
    className="inline-flex items-center gap-2 rounded-full border border-border bg-bg3 px-3 py-1.5 text-xs font-semibold text-text"
    aria-pressed={enabled}
  >
    <span className={`h-2.5 w-2.5 rounded-full ${enabled ? "bg-green" : "bg-text2"}`} />
    {enabled ? "Beginner Mode" : "Technical Mode"}
  </button>
);

export default BeginnerModeToggle;
