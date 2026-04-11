import { io } from "socket.io-client";

import client from "./apiClient";
import { API_BASE_URL, API_PATHS, SOCKET_EVENTS } from "../utils/constants";

let socket = null;

export const createChatSocket = (token) => {
  if (socket) {
    socket.disconnect();
  }
  socket = io(API_BASE_URL, {
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
  return response.data?.items || [];
};

export const createConversation = async ({ title, scanId } = {}) => {
  const response = await client.post(API_PATHS.chatConversations, {
    title,
    scan_id: scanId,
  });
  return response.data;
};

export const getConversation = async (conversationId) => {
  const response = await client.get(API_PATHS.chatConversation(conversationId));
  return response.data;
};

export const deleteConversation = async (conversationId) => {
  const response = await client.delete(API_PATHS.chatConversation(conversationId));
  return response.data;
};

export const getConversationMessages = async (conversationId, page = 1, perPage = 50) => {
  const response = await client.get(API_PATHS.chatMessages(conversationId), {
    params: { page, per_page: perPage },
  });
  return response.data;
};
