import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createSocket,
  disconnectSocket,
  getSocket,
  joinScanRoom,
  onSocketEvent,
  sendChatMessage,
} from "../services/chatService";
import { acquireLock, releaseLock } from "../utils/storage";
import { SOCKET_EVENTS } from "../utils/constants";
import { useAuth } from "./useAuth";

export const useAIChat = (scanId) => {
  const { accessToken, user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState("idle");
  const [isStreaming, setIsStreaming] = useState(false);
  const [scanCompleteEvent, setScanCompleteEvent] = useState(null);
  const [lastOutgoing, setLastOutgoing] = useState({ text: "", at: 0 });

  useEffect(() => {
    if (!accessToken || !scanId) {
      return;
    }

    const socket = createSocket(accessToken);
    setStatus("connecting");

    const cleanupConnect = onSocketEvent("connect", () => {
      setStatus("connected");
      joinScanRoom(scanId);
    });

    const cleanupDisconnect = onSocketEvent("disconnect", () => {
      setStatus("disconnected");
      setIsStreaming(false);
    });

    const cleanupReconnect = onSocketEvent("reconnect_attempt", () => {
      setStatus("reconnecting");
    });

    const cleanupReconnectOk = onSocketEvent("reconnect", () => {
      setStatus("connected");
      joinScanRoom(scanId);
    });

    const cleanupError = onSocketEvent(SOCKET_EVENTS.error, (payload) => {
      setIsStreaming(false);
      setMessages((prev) => [
        ...prev,
        { role: "system", text: payload?.msg || "Chat connection error", done: true },
      ]);
    });

    const cleanupResponse = onSocketEvent(SOCKET_EVENTS.chatResponse, (payload) => {
      setIsStreaming(!payload?.is_final);
      setMessages((prev) => {
        if (!prev.length || prev[prev.length - 1].role !== "assistant" || prev[prev.length - 1].done) {
          return [
            ...prev,
            {
              role: "assistant",
              text: payload.chunk || "",
              done: Boolean(payload.is_final),
              provider: payload.provider_used,
            },
          ];
        }

        const next = [...prev];
        const last = next[next.length - 1];
        next[next.length - 1] = {
          ...last,
          text: `${last.text}${payload.chunk || ""}`,
          done: Boolean(payload.is_final),
          provider: payload.provider_used || last.provider,
        };
        return next;
      });
    });

    const cleanupScanComplete = onSocketEvent(SOCKET_EVENTS.scanComplete, (payload) => {
      if (!payload?.scan_id || payload.scan_id !== scanId) {
        return;
      }
      setScanCompleteEvent(payload);
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          text: `Scan complete. Health score: ${payload.health_score ?? "n/a"}.`,
          done: true,
        },
      ]);
    });

    return () => {
      cleanupConnect();
      cleanupDisconnect();
      cleanupReconnect();
      cleanupReconnectOk();
      cleanupError();
      cleanupResponse();
      cleanupScanComplete();
      socket.disconnect();
      disconnectSocket();
    };
  }, [accessToken, scanId]);

  const sendMessage = useCallback((text) => {
    const normalized = (text || "").trim();
    if (!scanId || !normalized || !getSocket()) {
      return;
    }

    const now = Date.now();
    if (isStreaming) {
      return;
    }
    if (lastOutgoing.text === normalized && now - lastOutgoing.at < 1000) {
      return;
    }

    const lockKey = `codescan:chat-lock:${scanId}`;
    if (!acquireLock(lockKey, 1500)) {
      return;
    }

    setLastOutgoing({ text: normalized, at: now });
    setMessages((prev) => [...prev, { role: "user", text: normalized }]);
    setIsStreaming(true);
    try {
      sendChatMessage(scanId, normalized, user?.id);
    } finally {
      releaseLock(lockKey);
    }
  }, [isStreaming, lastOutgoing.at, lastOutgoing.text, scanId, user?.id]);

  return useMemo(
    () => ({
      messages,
      sendMessage,
      status,
      isStreaming,
      scanCompleteEvent,
      clearMessages: () => setMessages([]),
    }),
    [isStreaming, messages, scanCompleteEvent, sendMessage, status]
  );
};
