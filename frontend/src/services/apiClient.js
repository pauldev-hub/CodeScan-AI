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
  const message = payload.error || error.message || "Unexpected request failure";
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
    if (error?.response?.status !== 401 || originalRequest.__retry) {
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
