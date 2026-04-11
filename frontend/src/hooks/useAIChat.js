import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createChatSocket,
  createConversation,
  disconnectChatSocket,
  getConversation,
  onChatSocketEvent,
  sendConversationMessage,
  startChatSession,
} from "../services/devChatService";
import { SOCKET_EVENTS } from "../utils/constants";
import { useAuth } from "./useAuth";

export const useAIChat = ({ scanId = null, conversationId = null, autoCreate = false } = {}) => {
  const { accessToken } = useAuth();
  const [status, setStatus] = useState("idle");
  const [activeConversationId, setActiveConversationId] = useState(conversationId);
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [scanCompleteEvent, setScanCompleteEvent] = useState(null);
  const activeConversationIdRef = useRef(conversationId);

  useEffect(() => {
    activeConversationIdRef.current = activeConversationId;
  }, [activeConversationId]);

  useEffect(() => {
    if (conversationId) {
      setActiveConversationId(conversationId);
    }
  }, [conversationId]);

  useEffect(() => {
    if (!accessToken) {
      return undefined;
    }

    createChatSocket(accessToken);
    setStatus("connecting");

    const cleanups = [
      onChatSocketEvent("connect", () => {
        setStatus("connected");
        if (activeConversationIdRef.current || scanId) {
          startChatSession({ conversationId: activeConversationIdRef.current, scanId });
        }
      }),
      onChatSocketEvent("disconnect", () => {
        setStatus("disconnected");
        setIsStreaming(false);
      }),
      onChatSocketEvent("reconnect_attempt", () => setStatus("reconnecting")),
      onChatSocketEvent(SOCKET_EVENTS.error, (payload) => {
        setMessages((prev) => [...prev, { id: `error-${prev.length}`, role: "system", content: payload?.msg || "Chat connection error" }]);
      }),
      onChatSocketEvent("chat_error", (payload) => {
        setIsStreaming(false);
        setMessages((prev) => [...prev, { id: `chat-error-${prev.length}`, role: "system", content: payload?.error || "Unable to send chat message" }]);
      }),
      onChatSocketEvent("chat_message_saved", (payload) => {
        if (payload?.conversation_id) {
          setActiveConversationId((current) => current || payload.conversation_id);
        }
      }),
      onChatSocketEvent(SOCKET_EVENTS.chatResponseChunk, (payload) => {
        setActiveConversationId((current) => current || payload?.conversation_id);
        setIsStreaming(true);
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last?.streaming) {
            const next = [...prev];
            next[next.length - 1] = { ...last, content: `${last.content}${payload?.chunk || ""}` };
            return next;
          }
          return [...prev, { id: `assistant-stream-${Date.now()}`, role: "assistant", content: payload?.chunk || "", streaming: true }];
        });
      }),
      onChatSocketEvent(SOCKET_EVENTS.chatResponseDone, (payload) => {
        setIsStreaming(false);
        setActiveConversationId((current) => current || payload?.conversation_id);
        setMessages((prev) => {
          if (!prev.length) {
            return [{ id: payload?.message_id || `assistant-${Date.now()}`, role: "assistant", content: payload?.full_content || "" }];
          }
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant" && last?.streaming) {
            next[next.length - 1] = {
              id: payload?.message_id || last.id,
              role: "assistant",
              content: payload?.full_content || last.content,
              provider: payload?.provider_used,
            };
            return next;
          }
          return [...next, { id: payload?.message_id || `assistant-${Date.now()}`, role: "assistant", content: payload?.full_content || "", provider: payload?.provider_used }];
        });
      }),
      onChatSocketEvent(SOCKET_EVENTS.scanComplete, (payload) => {
        if (!payload?.scan_id || (scanId && payload.scan_id !== scanId)) {
          return;
        }
        setScanCompleteEvent(payload);
      }),
      onChatSocketEvent(SOCKET_EVENTS.roomJoined, (payload) => {
        if (payload?.conversation_id) {
          setActiveConversationId(payload.conversation_id);
        }
      }),
    ];

    return () => {
      cleanups.forEach((cleanup) => cleanup?.());
      disconnectChatSocket();
    };
  }, [accessToken, scanId]);

  useEffect(() => {
    let cancelled = false;
    const ensureConversation = async () => {
      if (!autoCreate || activeConversationId || !scanId) {
        return;
      }
      const created = await createConversation({ title: "Scan Chat", scanId });
      if (!cancelled) {
        setActiveConversationId(created.id);
        startChatSession({ conversationId: created.id, scanId });
      }
    };
    ensureConversation();
    return () => {
      cancelled = true;
    };
  }, [activeConversationId, autoCreate, scanId]);

  useEffect(() => {
    let cancelled = false;
    const loadConversation = async () => {
      if (!activeConversationId) {
        setMessages([]);
        return;
      }
      const payload = await getConversation(activeConversationId);
      if (!cancelled) {
        setMessages(payload.messages || []);
        startChatSession({ conversationId: activeConversationId, scanId });
      }
    };
    loadConversation();
    return () => {
      cancelled = true;
    };
  }, [activeConversationId, scanId]);

  const sendMessage = useCallback(
    async (text) => {
      const normalized = (text || "").trim();
      if (!normalized || isStreaming) {
        return;
      }

      let nextConversationId = activeConversationIdRef.current;
      if (!nextConversationId && autoCreate) {
        const created = await createConversation({ title: normalized.slice(0, 80), scanId });
        nextConversationId = created.id;
        setActiveConversationId(created.id);
        startChatSession({ conversationId: created.id, scanId });
      }
      if (!nextConversationId) {
        return;
      }

      setMessages((prev) => [...prev, { id: `user-${Date.now()}`, role: "user", content: normalized }]);
      setIsStreaming(true);
      sendConversationMessage({ conversationId: nextConversationId, scanId, message: normalized });
    },
    [autoCreate, isStreaming, scanId]
  );

  return useMemo(
    () => ({
      activeConversationId,
      setActiveConversationId,
      messages,
      sendMessage,
      status,
      isStreaming,
      scanCompleteEvent,
      clearMessages: () => setMessages([]),
    }),
    [activeConversationId, isStreaming, messages, scanCompleteEvent, sendMessage, status]
  );
};
