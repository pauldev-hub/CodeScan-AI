import { io } from "socket.io-client";

import client from "./apiClient";
import { API_PATHS, SOCKET_BASE_URL, SOCKET_EVENTS } from "../utils/constants";

let socket = null;

const unwrapPayload = (payload) => payload?.data ?? payload ?? {};

const normalizeMessage = (item) => ({
  id: item?.id,
  role: item?.role || "system",
  content: item?.content || "",
  feedback: item?.feedback ?? null,
  created_at: item?.created_at ?? null,
});

const normalizeConversation = (item) => ({
  id: item?.id,
  title: item?.title || "New Chat",
  preview: item?.preview || "",
  scan_id: item?.scan_id ?? null,
  created_at: item?.created_at ?? null,
  updated_at: item?.updated_at ?? item?.created_at ?? null,
  message_count: Number(item?.message_count || 0),
});

export const createChatSocket = (token) => {
  if (socket) {
    socket.disconnect();
  }
  socket = io(SOCKET_BASE_URL, {
    transports: ["websocket", "polling"],
    auth: { token },
  });
  return socket;
};

export const disconnectChatSocket = () => {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
};

export const getChatSocket = () => socket;

export const onChatSocketEvent = (eventName, handler) => {
  if (!socket) {
    return () => {};
  }
  socket.on(eventName, handler);
  return () => socket.off(eventName, handler);
};

export const startChatSession = ({ conversationId, scanId }) => {
  if (!socket) {
    return;
  }
  socket.emit(SOCKET_EVENTS.chatStart, {
    conversation_id: conversationId,
    scan_id: scanId,
  });
};

export const sendConversationMessage = ({ conversationId, scanId, message }) => {
  if (!socket) {
    throw new Error("Chat socket not initialized");
  }
  socket.emit(SOCKET_EVENTS.chatMessage, {
    conversation_id: conversationId,
    scan_id: scanId,
    message,
  });
};

export const listConversations = async () => {
  const response = await client.get(API_PATHS.chatConversations);
  const payload = unwrapPayload(response.data);
  const items = Array.isArray(payload.items) ? payload.items : [];
  return items.map(normalizeConversation);
};

export const createConversation = async ({ title, scanId } = {}) => {
  const response = await client.post(API_PATHS.chatConversations, {
    title,
    scan_id: scanId,
  });
  return normalizeConversation(unwrapPayload(response.data));
};

export const getConversation = async (conversationId) => {
  const response = await client.get(API_PATHS.chatConversation(conversationId));
  const payload = unwrapPayload(response.data);
  const messages = Array.isArray(payload.messages)
    ? payload.messages
    : Array.isArray(payload.items)
      ? payload.items
      : [];

  return {
    ...normalizeConversation(payload),
    messages: messages.map(normalizeMessage),
  };
};

export const deleteConversation = async (conversationId) => {
  const response = await client.delete(API_PATHS.chatConversation(conversationId));
  return response.data;
};

export const getConversationMessages = async (conversationId, page = 1, perPage = 50) => {
  const response = await client.get(API_PATHS.chatMessages(conversationId), {
    params: { page, per_page: perPage },
  });
  const payload = unwrapPayload(response.data);
  return {
    ...payload,
    items: Array.isArray(payload.items) ? payload.items.map(normalizeMessage) : [],
  };
};

export const setConversationMessageFeedback = async ({ conversationId, messageId, feedback }) => {
  const response = await client.patch(API_PATHS.chatMessageFeedback(conversationId, messageId), {
    feedback,
  });
  const payload = unwrapPayload(response.data);
  return normalizeMessage(payload?.message || payload);
};
