const LoadingSpinner = ({ label = "Loading..." }) => (
  <div className="inline-flex items-center gap-2 text-sm text-text2" role="status" aria-live="polite">
    <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent" />
    <span>{label}</span>
  </div>
);

export default LoadingSpinner;
