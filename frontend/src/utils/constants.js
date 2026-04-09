export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "http://localhost:5000";

export const APP_ROUTES = {
  landing: "/",
  login: "/login",
  signup: "/signup",
  dashboard: "/dashboard",
  scan: "/scan",
  results: "/results/:scanId",
  sharedReport: "/report/shared/:shareUuid",
  admin: "/admin",
  adminQueue: "/admin/queue",
  adminIncidents: "/admin/incidents",
};

export const THEME_STORAGE_KEY = "codescan-theme";
export const AUTH_STORAGE_KEY = "codescan-auth";
export const BEGINNER_MODE_STORAGE_KEY = "codescan-beginner-mode";

export const SOCKET_EVENTS = {
  chatMessage: "chat_message",
  chatResponse: "chat_response",
  scanComplete: "scan_complete",
  joinScanRoom: "join_scan_room",
  roomJoined: "room_joined",
  error: "error",
};

export const API_PATHS = {
  login: "/api/auth/login",
  signup: "/api/auth/register",
  refresh: "/api/auth/refresh",
  logout: "/api/auth/logout",
  scanUrl: "/api/scan/url",
  scanPaste: "/api/scan/paste",
  scanUpload: "/api/scan/upload",
  scanStatus: (scanId) => `/api/scan/${scanId}/status`,
  scanResults: (scanId) => `/api/scan/${scanId}/results`,
  scanHistory: "/api/scan/history",
  shareReport: (scanId) => `/api/report/${scanId}/share`,
  revokeShare: (scanId) => `/api/report/${scanId}/revoke`,
  sharedReport: (uuid) => `/api/report/shared/${uuid}`,
};
