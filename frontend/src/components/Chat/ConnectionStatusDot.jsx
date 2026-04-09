const statusStyles = {
  connected: {
    dot: "bg-green animate-pulseDot",
    label: "Connected",
  },
  reconnecting: {
    dot: "bg-yellow animate-pulseDot",
    label: "Reconnecting",
  },
  disconnected: {
    dot: "bg-red",
    label: "Disconnected",
  },
  connecting: {
    dot: "bg-text2 animate-pulseDot",
    label: "Connecting",
  },
};

const ConnectionStatusDot = ({ status }) => {
  const visual = statusStyles[status] || statusStyles.connecting;

  return (
    <span className="inline-flex items-center gap-1 text-xs text-text2" aria-live="polite">
      <span className={`h-2 w-2 rounded-full ${visual.dot}`} />
      {visual.label}
    </span>
  );
};

export default ConnectionStatusDot;
