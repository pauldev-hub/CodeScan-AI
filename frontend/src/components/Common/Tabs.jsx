import clsx from "clsx";

const Tabs = ({ tabs, activeTab, onChange }) => (
  <div className="inline-flex rounded-full border border-border bg-bg3 p-1">
    {tabs.map((tab) => (
      <button
        key={tab.value}
        type="button"
        onClick={() => onChange(tab.value)}
        className={clsx(
          "rounded-full px-3 py-1.5 text-sm font-semibold transition-colors",
          activeTab === tab.value ? "bg-bg2 text-accent shadow-sm" : "text-text2"
        )}
      >
        {tab.label}
      </button>
    ))}
  </div>
);

export default Tabs;
