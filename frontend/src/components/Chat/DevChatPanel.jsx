import {
  ChevronDown,
  Copy,
  FolderOpen,
  ImagePlus,
  Paperclip,
  Pencil,
  Plus,
  RotateCcw,
  SendHorizonal,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  WandSparkles,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import Button from "../Common/Button";
import ConnectionStatusDot from "./ConnectionStatusDot";

const defaultQuickPrompts = [
  "Explain the highest-risk issue in plain English.",
  "What should I fix first and why?",
  "Search code for auth middleware",
  "Roast this code gently.",
];

const tonePrompts = [
  { label: "Helpful", prompt: "Give me the clearest next step here." },
  { label: "Roast", prompt: "Roast this code gently but make it useful." },
  { label: "Savage", prompt: "Be brutal and roast the weakest part of this code." },
];

const MAX_ATTACHMENT_BYTES = 300 * 1024;
const TEXT_FILE_EXTENSIONS = [
  ".py",
  ".js",
  ".jsx",
  ".ts",
  ".tsx",
  ".json",
  ".md",
  ".txt",
  ".yml",
  ".yaml",
  ".html",
  ".css",
  ".sql",
  ".env",
  ".toml",
];

const isTextLikeFile = (file) => {
  const name = (file?.name || "").toLowerCase();
  return file?.type?.startsWith("text/") || TEXT_FILE_EXTENSIONS.some((ext) => name.endsWith(ext));
};

const buildAttachmentBlock = async (fileList, sourceLabel) => {
  const files = Array.from(fileList || []);
  if (!files.length) {
    return "";
  }

  const sections = [];
  for (const file of files) {
    const sizeLabel = `${Math.max(1, Math.round(file.size / 1024))}KB`;
    if (file.size > MAX_ATTACHMENT_BYTES) {
      sections.push(`Attachment (${sourceLabel}): ${file.name} [${sizeLabel}]\nSkipped: file too large for inline chat context.`);
      continue;
    }

    if (!isTextLikeFile(file)) {
      sections.push(`Attachment (${sourceLabel}): ${file.name} [${sizeLabel}]\nBinary/media attachment noted. Describe what you want analyzed from it.`);
      continue;
    }

    const raw = await file.text();
    const clipped = raw.length > 8000 ? `${raw.slice(0, 8000)}\n[truncated for chat context]` : raw;
    sections.push(`Attachment (${sourceLabel}): ${file.name} [${sizeLabel}]\n${clipped}`);
  }

  return sections.join("\n\n");
};

const ActionIcon = ({ label, title, onClick, active = false, children }) => (
  <button
    type="button"
    onClick={onClick}
    className={`inline-flex h-8 w-8 items-center justify-center rounded-full border transition-colors ${
      active ? "border-[color:var(--accent)] bg-[color:var(--accent)]/15 text-accent" : "border-border bg-bg3/70 text-text2 hover:text-text"
    }`}
    aria-label={label}
    title={title || label}
  >
    {children}
  </button>
);

const MessageBubble = ({ message, copied, onCopy, onEdit, onFeedback }) => {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[92%] rounded-[26px] px-4 py-3 text-sm leading-6 shadow-[0_14px_28px_rgba(0,0,0,0.12)] ${
          isUser
            ? "bg-[linear-gradient(145deg,#f0c08c,#e2ac73)] text-[#26170f]"
            : message.role === "system"
              ? "border border-border bg-bg3/70 text-text2"
              : "border border-border bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01))] text-text"
        }`}
      >
        {isAssistant ? (
          <div className="mb-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-text3">
            <Sparkles size={12} className="text-accent" />
            Assistant
          </div>
        ) : null}

        <div className="whitespace-pre-wrap">{message.content}</div>

        {isUser ? (
          <div className="mt-3 flex items-center justify-end gap-2 border-t border-[#2f231f]/35 pt-2">
            <ActionIcon label="Copy prompt" onClick={() => onCopy(message.content, message.id)} active={copied}>
              <Copy size={13} />
            </ActionIcon>
            <ActionIcon label="Edit prompt" onClick={() => onEdit(message.content)}>
              <Pencil size={13} />
            </ActionIcon>
          </div>
        ) : null}

        {isAssistant && !message.streaming && message.id ? (
          <div className="mt-3 flex items-center gap-2 border-t border-border/60 pt-2">
            <ActionIcon
              label="Like response"
              onClick={() => onFeedback(message.id, message.feedback === "like" ? null : "like")}
              active={message.feedback === "like"}
            >
              <ThumbsUp size={13} />
            </ActionIcon>
            <ActionIcon
              label="Dislike response"
              onClick={() => onFeedback(message.id, message.feedback === "dislike" ? null : "dislike")}
              active={message.feedback === "dislike"}
            >
              <ThumbsDown size={13} />
            </ActionIcon>
          </div>
        ) : null}
      </div>
    </div>
  );
};

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
  onMessageFeedback,
  quickPrompts = defaultQuickPrompts,
  minimalHeader = false,
}) => {
  const messagesRef = useRef(null);
  const fileInputRef = useRef(null);
  const imageInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const textareaRef = useRef(null);
  const quickMenuRef = useRef(null);
  const [quickMenuOpen, setQuickMenuOpen] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState(null);
  const [composerFocused, setComposerFocused] = useState(false);

  const canSend = useMemo(() => Boolean(draft.trim()) && !isStreaming, [draft, isStreaming]);
  const compactComposer = !composerFocused && !draft.trim() && messages.length > 0;

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (folderInputRef.current) {
      folderInputRef.current.setAttribute("webkitdirectory", "");
      folderInputRef.current.setAttribute("directory", "");
    }
  }, []);

  useEffect(() => {
    if (!quickMenuOpen) {
      return undefined;
    }

    const handleOutsideClick = (event) => {
      if (!quickMenuRef.current?.contains(event.target)) {
        setQuickMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, [quickMenuOpen]);

  const handleAttachmentSelection = async (event, sourceLabel) => {
    const block = await buildAttachmentBlock(event?.target?.files || [], sourceLabel);
    if (block) {
      setDraft((prev) => `${(prev || "").trim()}${prev?.trim() ? "\n\n" : ""}${block}`);
    }
    if (event?.target) {
      event.target.value = "";
    }
  };

  const handleCopyPrompt = async (content, messageId) => {
    try {
      await navigator.clipboard.writeText(content || "");
      setCopiedMessageId(messageId || "copied");
      window.setTimeout(() => setCopiedMessageId(null), 1400);
    } catch {
      setCopiedMessageId(null);
    }
  };

  const handleEditPrompt = (content) => {
    setDraft(content || "");
    window.setTimeout(() => {
      textareaRef.current?.focus();
      const nextText = content || "";
      textareaRef.current?.setSelectionRange(nextText.length, nextText.length);
    }, 0);
  };

  return (
    <aside className="codescan-glass flex max-h-[calc(100vh-110px)] min-h-[560px] flex-col rounded-[30px] bg-[color:var(--panel)] p-3 md:p-4">
      <div className={`flex flex-wrap items-center justify-between gap-3 ${minimalHeader ? "mb-2 border-b border-border pb-3" : "rounded-[24px] border border-border bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01))] p-4"}`}>
        <div className="flex items-center gap-2">
          {!minimalHeader ? <p className="text-base font-semibold text-text">{title}</p> : null}
          <ConnectionStatusDot status={status} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {tonePrompts.map((item) => (
            <button
              key={item.label}
              type="button"
              onClick={() => onQuickPrompt?.(item.prompt)}
              className="rounded-full border border-border bg-bg3/70 px-3 py-1.5 text-xs font-medium text-text2 transition-colors hover:text-text"
            >
              {item.label}
            </button>
          ))}
          {onClear ? (
            <ActionIcon label="Clear chat" onClick={onClear}>
              <RotateCcw size={13} />
            </ActionIcon>
          ) : null}
          {onClose ? (
            <ActionIcon label="Close chat" onClick={onClose}>
              <X size={13} />
            </ActionIcon>
          ) : null}
        </div>
        {!minimalHeader && subtitle ? (
          <p className="w-full text-sm text-text2">
            {subtitle}
          </p>
        ) : null}
      </div>

      <div ref={messagesRef} className="codescan-chat-scroll flex min-h-0 flex-1 flex-col gap-3 overflow-auto pr-1">
        {!messages.length ? (
          <div className="rounded-[24px] border border-border bg-bg3/70 px-4 py-4 text-sm text-text2">
            DevChat is ready. Try a fix question, a repo search, or a playful roast.
          </div>
        ) : null}
        {messages.map((message) => (
          <MessageBubble
            key={message.id || `${message.role}-${message.content.slice(0, 20)}`}
            message={message}
            copied={copiedMessageId === message.id}
            onCopy={handleCopyPrompt}
            onEdit={handleEditPrompt}
            onFeedback={onMessageFeedback || (() => {})}
          />
        ))}
      </div>

      <div className={`mt-3 rounded-[24px] border border-border bg-bg3/70 p-2.5 transition-all ${compactComposer ? "pb-2" : ""}`}>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(event) => handleAttachmentSelection(event, "file")}
        />
        <input
          ref={imageInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(event) => handleAttachmentSelection(event, "image")}
        />
        <input
          ref={folderInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(event) => handleAttachmentSelection(event, "folder")}
        />

        <div className="mb-2 flex flex-wrap items-center gap-1.5 border-b border-border pb-2">
          <div className="relative" ref={quickMenuRef}>
            <button
              type="button"
              onClick={() => setQuickMenuOpen((open) => !open)}
              className="inline-flex items-center gap-1 rounded-full border border-border bg-bg3 px-2.5 py-1 text-xs text-text2 transition-colors hover:text-text"
              aria-expanded={quickMenuOpen}
              aria-haspopup="menu"
              aria-label="Open quick DevChat questions"
            >
              <Plus size={12} />
              Prompts
              <ChevronDown size={12} className={`transition-transform ${quickMenuOpen ? "rotate-180" : ""}`} />
            </button>
            {quickMenuOpen ? (
              <div className="absolute left-0 top-[calc(100%+8px)] z-20 w-[300px] rounded-2xl border border-border bg-[color:var(--panel-strong)] p-2 shadow-[0_20px_45px_rgba(0,0,0,0.35)]">
                {(quickPrompts?.length ? quickPrompts : defaultQuickPrompts).map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => {
                      setQuickMenuOpen(false);
                      onQuickPrompt?.(prompt);
                    }}
                    className="w-full rounded-xl px-3 py-2 text-left text-xs text-text2 transition-colors hover:bg-bg3 hover:text-text"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-1 rounded-full border border-border bg-bg3 px-2.5 py-1 text-xs text-text2"
          >
            <Paperclip size={12} />
            Files
          </button>
          <button
            type="button"
            onClick={() => imageInputRef.current?.click()}
            className="inline-flex items-center gap-1 rounded-full border border-border bg-bg3 px-2.5 py-1 text-xs text-text2"
          >
            <ImagePlus size={12} />
            Images
          </button>
          <button
            type="button"
            onClick={() => folderInputRef.current?.click()}
            className="inline-flex items-center gap-1 rounded-full border border-border bg-bg3 px-2.5 py-1 text-xs text-text2"
          >
            <FolderOpen size={12} />
            Folder
          </button>
        </div>

        <textarea
          ref={textareaRef}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onFocus={() => setComposerFocused(true)}
          onBlur={() => setComposerFocused(false)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSend();
            }
          }}
          className={`w-full resize-none border-0 bg-transparent px-1 py-1 text-sm leading-6 text-text outline-none placeholder:text-text3 transition-all ${
            compactComposer ? "h-11 min-h-11 max-h-11" : "h-20 min-h-20 max-h-32"
          }`}
          placeholder="Ask about a finding, search the scanned code, request a rewrite, or switch on roast mode..."
          spellCheck="false"
        />
        <div className={`mt-2 flex items-center justify-between gap-3 border-t border-border pt-2 ${compactComposer ? "text-[11px]" : ""}`}>
          <p className={`text-text2 md:text-xs ${compactComposer ? "line-clamp-1 text-[10px]" : "text-[11px]"}`}>
            Enter sends. Shift+Enter adds a new line. DevChat can use scan context, memory notes, and quick repo-style search.
          </p>
          <Button type="button" onClick={onSend} disabled={!canSend} size="sm">
            <WandSparkles size={14} />
            <SendHorizonal size={14} />
          </Button>
        </div>
      </div>
    </aside>
  );
};

export default DevChatPanel;
