import { MessageSquarePlus, Search, Trash2 } from "lucide-react";
import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";

import ChatBoundary from "../components/Chat/ChatBoundary";
import DevChatPanel from "../components/Chat/DevChatPanel";
import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
import { useAIChat } from "../hooks/useAIChat";
import { createConversation, deleteConversation, listConversations } from "../services/devChatService";
import { formatDateInIndia, parseApiDate } from "../utils/datetime";

const groupLabelForDate = (isoValue) => {
  if (!isoValue) {
    return "Older";
  }
  const date = new Date(isoValue);
  const parsedDate = parseApiDate(isoValue);
  const sourceDate = parsedDate || date;
  if (Number.isNaN(sourceDate.getTime())) {
    return "Older";
  }
  const now = new Date();
  const diff = Math.floor((now.setHours(0, 0, 0, 0) - new Date(sourceDate).setHours(0, 0, 0, 0)) / 86400000);
  if (diff <= 0) return "Today";
  if (diff === 1) return "Yesterday";
  if (diff <= 7) return "Last 7 Days";
  if (diff <= 30) return "This Month";
  return "Older";
};

const quickPrompts = [
  "Search code for authentication middleware",
  "Roast this code gently but keep it useful.",
  "What should I fix first and why?",
  "Give me the cleanest rewrite strategy for this bug.",
];

const DevChatPage = () => {
  const [conversations, setConversations] = useState([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [conversationsError, setConversationsError] = useState(null);
  const [draft, setDraft] = useState("");
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const deferredSearch = useDeferredValue(searchQuery);
  const {
    messages,
    sendMessage,
    status,
    isStreaming,
    activeConversationId,
    setActiveConversationId,
    openConversation,
    rateMessage,
    conversationLoading,
    clearMessages,
  } = useAIChat({
    conversationId: selectedConversationId,
    autoCreate: true,
  });

  const loadConversations = useCallback(async () => {
    setConversationsLoading(true);
    setConversationsError(null);
    try {
      const items = await listConversations();
      setConversations(items);

      const hasSelected = selectedConversationId
        ? items.some((item) => item.id === selectedConversationId)
        : false;
      if (!hasSelected) {
        setSelectedConversationId(items[0]?.id || null);
      }
      return items;
    } catch (error) {
      setConversationsError(error?.message || "Unable to load conversations right now.");
      setConversations([]);
      setSelectedConversationId(null);
      clearMessages();
      return [];
    } finally {
      setConversationsLoading(false);
    }
  }, [clearMessages, selectedConversationId]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (activeConversationId && activeConversationId !== selectedConversationId) {
      setSelectedConversationId(activeConversationId);
      loadConversations();
    }
  }, [activeConversationId, loadConversations, selectedConversationId]);

  const filteredConversations = useMemo(() => {
    const normalizedSearch = deferredSearch.trim().toLowerCase();
    if (!normalizedSearch) {
      return conversations;
    }
    return conversations.filter((item) =>
      [item.title, item.preview]
        .join(" ")
        .toLowerCase()
        .includes(normalizedSearch)
    );
  }, [conversations, deferredSearch]);

  const grouped = useMemo(
    () =>
      filteredConversations.reduce((acc, item) => {
        const label = groupLabelForDate(item.updated_at);
        acc[label] = [...(acc[label] || []), item];
        return acc;
      }, {}),
    [filteredConversations]
  );

  const selectedConversation = conversations.find((item) => item.id === selectedConversationId) || null;

  const onNewChat = async () => {
    setConversationsError(null);
    try {
      const created = await createConversation({ title: "New Chat" });
      setSelectedConversationId(created.id);
      setActiveConversationId(created.id);
      setDraft("");
      clearMessages();
      await loadConversations();
    } catch (error) {
      setConversationsError(error?.message || "Unable to create a new conversation.");
    }
  };

  const onDeleteConversation = async (conversationId) => {
    setConversationsError(null);
    try {
      await deleteConversation(conversationId);
      if (selectedConversationId === conversationId) {
        setSelectedConversationId(null);
        clearMessages();
      }
      await loadConversations();
    } catch (error) {
      setConversationsError(error?.message || "Unable to delete this conversation.");
    }
  };

  const onSelectConversation = async (conversationId) => {
    if (!conversationId) {
      return;
    }
    setConversationsError(null);
    setSelectedConversationId(conversationId);
    await openConversation(conversationId);
  };

  const onSend = async () => {
    const message = draft.trim();
    if (!message) {
      return;
    }
    try {
      setConversationsError(null);
      await sendMessage(message);
      setDraft("");
      await loadConversations();
    } catch (error) {
      setConversationsError(error?.message || "Unable to send this message right now.");
    }
  };

  return (
    <main className="space-y-5">
      <ScrollReveal>
        <div className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
          <Card className="flex h-[calc(100vh-110px)] flex-col overflow-hidden xl:sticky xl:top-[84px]">
            <div className="border-b border-border pb-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.24em] text-accent">DevChat</p>
                  <h1 className="mt-3 text-2xl font-bold text-text">Conversation workspace</h1>
                  <p className="mt-2 text-sm text-text2">Compact history, cleaner sorting, and faster jump-back into earlier threads.</p>
                </div>
                <Button size="sm" onClick={onNewChat}>
                  <MessageSquarePlus size={14} />
                  New
                </Button>
              </div>

              <div className="mt-4 rounded-[20px] border border-border bg-bg3/70 p-3">
                <div className="flex items-center gap-2 rounded-2xl border border-border bg-bg2 px-3 py-2">
                  <Search size={14} className="text-text3" />
                  <input
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    className="w-full border-0 bg-transparent text-sm text-text outline-none placeholder:text-text3"
                    placeholder="Search chats..."
                  />
                </div>
                {selectedConversation ? (
                  <div className="mt-3 flex items-center justify-between gap-3 text-xs text-text2">
                    <span>{selectedConversation.message_count} messages</span>
                    <span>{groupLabelForDate(selectedConversation.updated_at)}</span>
                  </div>
                ) : (
                  <p className="mt-3 text-xs text-text2">Pick a thread or start a new one.</p>
                )}
              </div>
            </div>

            <div className="mt-4 flex-1 space-y-4 overflow-auto pr-1">
              {conversationsError ? (
                <div className="rounded-xl border border-[color:var(--red)]/40 bg-[color:var(--red)]/10 px-3 py-2 text-sm text-[color:var(--red)]">
                  {conversationsError}
                </div>
              ) : null}

              {Object.entries(grouped).map(([label, items]) => (
                <div key={label}>
                  <p className="text-[11px] uppercase tracking-[0.16em] text-text3">{label}</p>
                  <div className="mt-2 space-y-2">
                    {items.map((item) => (
                      <div
                        key={item.id}
                        className={`rounded-[22px] border p-3 transition-colors ${
                          selectedConversationId === item.id
                            ? "border-[color:var(--accent)] bg-[color:var(--accent-glow)]"
                            : "border-border bg-bg3/60 hover:bg-bg3/80"
                        }`}
                      >
                        <button type="button" onClick={() => onSelectConversation(item.id)} className="w-full text-left">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold text-text">{item.title}</p>
                              <p className="mt-1 line-clamp-2 text-xs leading-5 text-text2">{item.preview || "Empty conversation"}</p>
                            </div>
                            <span className="shrink-0 rounded-full border border-border bg-bg2 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-text3">
                              {item.message_count}
                            </span>
                          </div>
                        </button>
                        <div className="mt-3 flex items-center justify-between gap-3">
                          <p className="text-[11px] text-text3">{formatDateInIndia(item.updated_at)}</p>
                          <button
                            type="button"
                            onClick={() => onDeleteConversation(item.id)}
                            className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-border bg-bg2 text-text2 transition-colors hover:text-text"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {conversationsLoading ? <p className="text-sm text-text2">Loading conversations...</p> : null}
              {!conversationsLoading && !filteredConversations.length ? (
                <p className="text-sm text-text2">
                  {searchQuery ? "No conversations match that search yet." : "No conversations yet."}
                </p>
              ) : null}
            </div>
          </Card>

          <ChatBoundary>
            <div className="xl:sticky xl:top-[84px]">
            <DevChatPanel
              title="CodeScan DevChat"
              subtitle="Natural replies, smarter memory, local code search, news lookup support, and roast mode when you want it."
              messages={
                conversationLoading
                  ? [{ id: "conversation-loading", role: "system", content: "Loading conversation..." }]
                  : messages
              }
              draft={draft}
              setDraft={setDraft}
              onSend={onSend}
              onClear={clearMessages}
              status={status}
              isStreaming={isStreaming}
              onMessageFeedback={rateMessage}
              quickPrompts={quickPrompts}
              onQuickPrompt={async (prompt) => {
                try {
                  setConversationsError(null);
                  setDraft(prompt);
                  await sendMessage(prompt);
                  setDraft("");
                  await loadConversations();
                } catch (error) {
                  setConversationsError(error?.message || "Unable to send this quick prompt.");
                }
              }}
            />
            </div>
          </ChatBoundary>
        </div>
      </ScrollReveal>
    </main>
  );
};

export default DevChatPage;
