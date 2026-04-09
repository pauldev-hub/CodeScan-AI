import ErrorBoundary from "../Common/ErrorBoundary";

const ChatBoundary = ({ children }) => (
  <ErrorBoundary
    fallback={({ message, reset }) => (
      <div className="h-full rounded-[10px] border border-red/40 bg-red/10 p-4 text-sm text-red">
        <p className="font-semibold">Chat temporarily unavailable</p>
        <p className="mt-1">{message}</p>
        <button type="button" className="mt-3 rounded-md border border-red px-3 py-1" onClick={reset}>
          Reconnect
        </button>
      </div>
    )}
  >
    {children}
  </ErrorBoundary>
);

export default ChatBoundary;
