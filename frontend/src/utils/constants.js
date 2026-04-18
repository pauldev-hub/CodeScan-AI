export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "http://localhost:5000";

export const SOCKET_BASE_URL = import.meta.env.VITE_SOCKET_URL || API_BASE_URL;

export const APP_ROUTES = {
  landing: "/",
  login: "/login",
  signup: "/signup",
  dashboard: "/dashboard",
  activity: "/activity",
  scan: "/scan",
  results: "/results/:scanId",
  chat: "/app/chat",
  settings: "/settings",
  sharedReport: "/report/shared/:shareUuid",
  sharedSummary: "/report/:shareUuid/summary",
  admin: "/admin",
  adminQueue: "/admin/queue",
  adminIncidents: "/admin/incidents",
};

export const THEME_STORAGE_KEY = "codescan-theme";
export const AUTH_STORAGE_KEY = "codescan-auth";
export const BEGINNER_MODE_STORAGE_KEY = "codescan-beginner-mode";

export const SOCKET_EVENTS = {
  chatMessage: "chat_message",
  chatStart: "chat_start",
  chatResponseChunk: "chat_response_chunk",
  chatResponseDone: "chat_response_done",
  scanComplete: "scan_complete",
  joinScanRoom: "join_scan_room",
  roomJoined: "room_joined",
  error: "error",
};

export const API_PATHS = {
  login: "/api/auth/login",
  guestLogin: "/api/auth/guest",
  signup: "/api/auth/register",
  refresh: "/api/auth/refresh",
  logout: "/api/auth/logout",
  scanUrl: "/api/scan/url",
  scanUrlPreview: "/api/scan/url/preview",
  scanPaste: "/api/scan/paste",
  scanUpload: "/api/scan/upload",
  scanStatus: (scanId) => `/api/scan/${scanId}/status`,
  scanResults: (scanId) => `/api/scan/${scanId}/results`,
  regenerateLearn: (scanId) => `/api/scan/${scanId}/learn/regenerate`,
  scanHistory: "/api/scan/history",
  shareReport: (scanId) => `/api/report/${scanId}/share`,
  revokeShare: (scanId) => `/api/report/${scanId}/revoke`,
  shareCard: (scanId) => `/api/report/${scanId}/share-card`,
  sharedReport: (uuid) => `/api/report/shared/${uuid}`,
  sharedSummary: (uuid) => `/api/report/shared/${uuid}/summary`,
  settings: "/api/settings",
  chatConversations: "/api/chat/conversations",
  chatConversation: (conversationId) => `/api/chat/conversations/${conversationId}`,
  chatMessages: (conversationId) => `/api/chat/conversations/${conversationId}/messages`,
  chatMessageFeedback: (conversationId, messageId) =>
    `/api/chat/conversations/${conversationId}/messages/${messageId}/feedback`,
};
