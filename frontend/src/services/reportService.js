import client from "./apiClient";
import { API_PATHS } from "../utils/constants";

export const createShareLink = async (scanId, expirationDays = 30) => {
  const response = await client.post(API_PATHS.shareReport(scanId), {
    expiration_days: expirationDays,
  });
  return response.data;
};

export const revokeShareLink = async (scanId) => {
  const response = await client.post(API_PATHS.revokeShare(scanId));
  return response.data;
};
