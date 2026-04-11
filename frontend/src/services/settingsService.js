import client from "./apiClient";
import { API_PATHS } from "../utils/constants";

export const getSettings = async () => {
  const response = await client.get(API_PATHS.settings);
  return response.data;
};

export const updateSettings = async (payload) => {
  const response = await client.put(API_PATHS.settings, payload);
  return response.data;
};
