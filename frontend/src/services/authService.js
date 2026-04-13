import client from "./apiClient";
import { API_PATHS } from "../utils/constants";

export const login = async ({ email, password }) => {
  const response = await client.post(API_PATHS.login, { email, password });
  return response.data;
};

export const loginGuest = async () => {
  const response = await client.post(API_PATHS.guestLogin, {});
  return response.data;
};

export const signup = async ({ email, username, password }) => {
  const response = await client.post(API_PATHS.signup, { email, username, password });
  return response.data;
};

export const logout = async (refreshToken) => {
  if (!refreshToken) {
    return;
  }
  await client.post(API_PATHS.logout, { refresh_token: refreshToken });
};
