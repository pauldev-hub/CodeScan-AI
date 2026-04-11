import { MessageSquarePlus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import ChatBoundary from "../components/Chat/ChatBoundary";
import DevChatPanel from "../components/Chat/DevChatPanel";
import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
import { useAIChat } from "../hooks/useAIChat";
import { createConversation, deleteConversation, listConversations } from "../services/devChatService";

const groupLabelForDate = (isoValue) => {
  const date = new Date(isoValue);
  const now = new Date();
  const diff = Math.floor((now.setHours(0, 0, 0, 0) - new Date(date).setHours(0, 0, 0, 0)) / 86400000);
  if (diff <= 0) return "Today";
  if (diff === 1) return "Yesterday";
  if (diff <= 7) return "Last 7 Days";
  return "Older";
};

const DevChatPage = () => {
  const [conversations, setConversations] = useState([]);
  const [draft, setDraft] = useState("");
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const { messages, sendMessage, status, isStreaming, activeConversationId, setActiveConversationId, clearMessages } = useAIChat({
    conversationId: selectedConversationId,
    autoCreate: false,
  });

  const loadConversations = useCallback(async () => {
    const items = await listConversations();
    setConversations(items);
    if (!selectedConversationId && items[0]?.id) {
      setSelectedConversationId(items[0].id);
    }
  }, [selectedConversationId]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (activeConversationId && activeConversationId !== selectedConversationId) {
      setSelectedConversationId(activeConversationId);
      loadConversations();
    }
  }, [activeConversationId, loadConversations, selectedConversationId]);

  const grouped = conversations.reduce((acc, item) => {
    const label = groupLabelForDate(item.updated_at);
    acc[label] = [...(acc[label] || []), item];
    return acc;
  }, {});

  const onNewChat = async () => {
    const created = await createConversation({ title: "New Chat" });
    setSelectedConversationId(created.id);
    setActiveConversationId(created.id);
    setDraft("");
    clearMessages();
    await loadConversations();
  };

  const onDeleteConversation = async (conversationId) => {
    await deleteConversation(conversationId);
    if (selectedConversationId === conversationId) {
      setSelectedConversationId(null);
      clearMessages();
    }
    await loadConversations();
  };

  const onSend = async () => {
    const message = draft.trim();
    if (!message) {
      return;
    }
    await sendMessage(message);
    setDraft("");
    await loadConversations();
  };

  return (
    <main className="space-y-5">
      <ScrollReveal>
        <div className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)]">
          <Card className="h-fit">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.24em] text-accent">DevChat</p>
                <h1 className="mt-3 text-2xl font-bold text-text">Persistent AI conversations</h1>
              </div>
              <Button size="sm" onClick={onNewChat}>
                <MessageSquarePlus size={14} />
                New Chat
              </Button>
            </div>
            <div className="mt-5 space-y-4">
              {Object.entries(grouped).map(([label, items]) => (
                <div key={label}>
                  <p className="text-[11px] uppercase tracking-[0.16em] text-text3">{label}</p>
                  <div className="mt-2 space-y-2">
                    {items.map((item) => (
                      <div
                        key={item.id}
                        className={`rounded-2xl border px-3 py-3 ${selectedConversationId === item.id ? "border-[color:var(--accent)] bg-bg2" : "border-border bg-bg3/70"}`}
                      >
                        <button type="button" onClick={() => setSelectedConversationId(item.id)} className="w-full text-left">
                          <p className="text-sm font-semibold text-text">{item.title}</p>
                          <p className="mt-1 text-xs text-text2">{item.preview || "Empty conversation"}</p>
                        </button>
                        <div className="mt-2 flex justify-end">
                          <button type="button" onClick={() => onDeleteConversation(item.id)} className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-border bg-bg3 text-text2">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {!conversations.length ? <p className="text-sm text-text2">No conversations yet.</p> : null}
            </div>
          </Card>

          <ChatBoundary>
            <DevChatPanel
              title="CodeScan DevChat"
              subtitle="Groq-first assistance with Gemini fallback, plus persistent history tied to your account."
              messages={messages}
              draft={draft}
              setDraft={setDraft}
              onSend={onSend}
              onClear={clearMessages}
              status={status}
              isStreaming={isStreaming}
              onQuickPrompt={async (prompt) => {
                setDraft(prompt);
                await sendMessage(prompt);
                setDraft("");
                await loadConversations();
              }}
            />
          </ChatBoundary>
        </div>
      </ScrollReveal>
    </main>
  );
};

export default DevChatPage;
