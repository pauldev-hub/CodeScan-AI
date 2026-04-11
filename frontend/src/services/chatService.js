import { io } from "socket.io-client";

import { API_BASE_URL, SOCKET_EVENTS } from "../utils/constants";

let socket = null;

export const createSocket = (token) => {
  if (socket) {
    socket.disconnect();
  }

  socket = io(API_BASE_URL, {
    transports: ["websocket", "polling"],
    auth: {
      token,
    },
  });

  return socket;
};

export const getSocket = () => socket;

export const joinScanRoom = (scanId) => {
  if (!socket || !scanId) {
    return;
  }
  socket.emit(SOCKET_EVENTS.joinScanRoom, { scan_id: scanId });
};

export const sendChatMessage = (scanId, message, userId, history = []) => {
  if (!socket) {
    throw new Error("Socket not initialized");
  }
  socket.emit(SOCKET_EVENTS.chatMessage, {
    scan_id: scanId,
    message,
    user_id: userId,
    history,
  });
};

export const onSocketEvent = (eventName, handler) => {
  if (!socket) {
    return () => {};
  }
  socket.on(eventName, handler);
  return () => socket.off(eventName, handler);
};

export const disconnectSocket = () => {
  if (!socket) {
    return;
  }
  socket.disconnect();
  socket = null;
};
