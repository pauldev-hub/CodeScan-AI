import client from "./apiClient";
import { API_PATHS } from "../utils/constants";

const SCAN_SUBMIT_TIMEOUT_MS = 120000;
const SCAN_READ_TIMEOUT_MS = 45000;

export const submitScanByUrl = async (githubUrl) => {
  const response = await client.post(
    API_PATHS.scanUrl,
    { github_url: githubUrl },
    { timeout: SCAN_SUBMIT_TIMEOUT_MS }
  );
  return response.data;
};

export const submitScanByPaste = async (code, language = "text") => {
  const response = await client.post(
    API_PATHS.scanPaste,
    { code, language },
    { timeout: SCAN_SUBMIT_TIMEOUT_MS }
  );
  return response.data;
};

export const submitScanByUpload = async (files) => {
  const formData = new FormData();
  files.forEach((file) => formData.append("file", file));

  const response = await client.post(API_PATHS.scanUpload, formData, {
    timeout: SCAN_SUBMIT_TIMEOUT_MS,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const getScanStatus = async (scanId, signal) => {
  const response = await client.get(API_PATHS.scanStatus(scanId), {
    signal,
    timeout: SCAN_READ_TIMEOUT_MS,
  });
  return response.data;
};

export const getScanResults = async (scanId, signal) => {
  const response = await client.get(API_PATHS.scanResults(scanId), {
    signal,
    timeout: SCAN_READ_TIMEOUT_MS,
  });
  return response.data;
};

export const regenerateLearnContent = async (scanId) => {
  const response = await client.post(API_PATHS.regenerateLearn(scanId));
  return response.data;
};

export const getScanHistory = async (page = 1, perPage = 10, signal) => {
  const response = await client.get(API_PATHS.scanHistory, {
    params: { page, per_page: perPage },
    signal,
    timeout: SCAN_READ_TIMEOUT_MS,
  });
  return response.data;
};

export const deleteScan = async (scanId) => {
  const response = await client.delete(API_PATHS.scanStatus(scanId).replace("/status", ""));
  return response.data;
};
