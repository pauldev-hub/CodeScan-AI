import axios from "axios";

import { API_BASE_URL, API_PATHS } from "../utils/constants";

const publicClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

export const getSharedSummary = async (shareUuid) => {
  const response = await publicClient.get(API_PATHS.sharedSummary(shareUuid));
  return response.data;
};
