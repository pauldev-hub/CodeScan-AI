import { RotateCcw, SendHorizonal, Sparkles, X } from "lucide-react";
import { useEffect, useRef } from "react";

import Button from "../Common/Button";
import ConnectionStatusDot from "./ConnectionStatusDot";

const quickPrompts = [
  "Explain the highest-risk issue in plain English.",
  "What should I fix first and why?",
  "Show me the safest remediation steps.",
  "Simulate how an attacker would exploit this.",
];

const MessageBubble = ({ message }) => (
  <div
    className={`max-w-[92%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 ${
      message.role === "user"
        ? "ml-auto bg-[linear-gradient(135deg,var(--accent),var(--accent-2))] text-[#23150c]"
        : message.role === "system"
          ? "border border-border bg-bg3/70 text-text2"
          : "bg-bg3 text-text"
    }`}
  >
    {message.role === "assistant" ? (
      <div className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-text3">
        <Sparkles size={12} className="text-accent" />
        Assistant
      </div>
    ) : null}
    {message.content}
  </div>
);

const DevChatPanel = ({
  title = "DevChat",
  subtitle,
  messages,
  draft,
  setDraft,
  onSend,
  onClose,
  onClear,
  status,
  isStreaming,
  onQuickPrompt,
}) => {
  const messagesRef = useRef(null);

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <aside className="codescan-glass rounded-[26px] bg-[color:var(--panel)] p-4">
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <p className="text-sm font-semibold text-text">{title}</p>
          <p className="mt-1 text-xs text-text2">{subtitle || "Ask about vulnerabilities, fixes, architecture, or debugging paths."}</p>
        </div>
        <div className="flex items-center gap-2">
          <ConnectionStatusDot status={status} />
          {onClear ? (
            <button type="button" onClick={onClear} className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-border bg-bg3 text-text" aria-label="Clear chat">
              <RotateCcw size={14} />
            </button>
          ) : null}
          {onClose ? (
            <button type="button" onClick={onClose} className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-border bg-bg3 text-text" aria-label="Close chat">
              <X size={14} />
            </button>
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {quickPrompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onQuickPrompt(prompt)}
            className="rounded-full border border-border bg-bg3 px-3 py-1.5 text-xs text-text2 transition-colors hover:text-text"
          >
            {prompt}
          </button>
        ))}
      </div>

      <div ref={messagesRef} className="codescan-chat-scroll mt-4 flex max-h-[420px] min-h-[320px] flex-col gap-3 overflow-auto pr-1">
        {!messages.length ? (
          <div className="rounded-2xl border border-border bg-bg3/70 px-4 py-3 text-sm text-text2">
            DevChat is ready. Ask about this scan, secure fixes, or general code questions.
          </div>
        ) : null}
        {messages.map((message) => (
          <MessageBubble key={message.id || `${message.role}-${message.content.slice(0, 20)}`} message={message} />
        ))}
      </div>

      <div className="mt-4 rounded-[22px] border border-border bg-bg3/70 p-3">
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSend();
            }
          }}
          className="min-h-[92px] w-full resize-none border-0 bg-transparent px-1 py-1 text-sm text-text outline-none placeholder:text-text3"
          placeholder="Ask about SQL injection, XSS, CSRF, JWT, logic bugs, safer refactors, or debugging steps..."
          spellCheck="false"
        />
        <div className="mt-3 flex items-center justify-between gap-3 border-t border-border pt-3">
          <p className="text-xs text-text2">Enter sends. Shift+Enter adds a new line.</p>
          <Button type="button" onClick={onSend} disabled={!draft.trim() || isStreaming} size="sm">
            <SendHorizonal size={14} />
            Send
          </Button>
        </div>
      </div>
    </aside>
  );
};

export default DevChatPanel;
