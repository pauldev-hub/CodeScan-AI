import axios from "axios";

import { API_BASE_URL, API_PATHS } from "../utils/constants";
import { getStoredJson, removeStored, setStoredJson } from "../utils/storage";
import { AUTH_STORAGE_KEY } from "../utils/constants";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

let refreshPromise = null;

const getAuthState = () => getStoredJson(AUTH_STORAGE_KEY, null);
const AUTH_ROUTES = new Set([API_PATHS.login, API_PATHS.signup, API_PATHS.refresh, API_PATHS.logout]);

client.interceptors.request.use((config) => {
  const authState = getAuthState();
  const token = authState?.accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

const mapApiError = (error) => {
  const status = error?.response?.status;
  const payload = error?.response?.data || {};
  const message = payload.error || payload.msg || payload.message || error.message || "Unexpected request failure";
  return {
    status,
    code: payload.status || "unknown_error",
    message,
    raw: error,
  };
};

const refreshAccessToken = async () => {
  const authState = getAuthState();
  if (!authState?.refreshToken) {
    throw new Error("No refresh token");
  }

  const response = await axios.post(`${API_BASE_URL}${API_PATHS.refresh}`, {
    refresh_token: authState.refreshToken,
  });

  const nextAuthState = {
    ...authState,
    accessToken: response.data.access_token,
    refreshToken: response.data.refresh_token,
  };
  setStoredJson(AUTH_STORAGE_KEY, nextAuthState);
  return nextAuthState;
};

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};
    const requestPath = originalRequest.url;
    const payload = error?.response?.data || {};
    const lowerMsg = String(payload.msg || payload.error || "").toLowerCase();
    const isJwtValidation422 =
      error?.response?.status === 422 &&
      (lowerMsg.includes("token") ||
        lowerMsg.includes("signature") ||
        lowerMsg.includes("subject") ||
        lowerMsg.includes("jwt"));
    const shouldSkipRefresh =
      AUTH_ROUTES.has(requestPath) ||
      !getAuthState()?.refreshToken;

    if ((error?.response?.status !== 401 && !isJwtValidation422) || originalRequest.__retry || shouldSkipRefresh) {
      return Promise.reject(mapApiError(error));
    }

    originalRequest.__retry = true;
    try {
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken();
      }
      const nextAuthState = await refreshPromise;
      refreshPromise = null;

      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${nextAuthState.accessToken}`;
      return client(originalRequest);
    } catch (refreshError) {
      refreshPromise = null;
      removeStored(AUTH_STORAGE_KEY);
      return Promise.reject(mapApiError(refreshError));
    }
  }
);

export { mapApiError };
export default client;
