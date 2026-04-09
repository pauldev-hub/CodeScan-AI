export const getStoredJson = (key, fallback = null) => {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
};

export const setStoredJson = (key, value) => {
  localStorage.setItem(key, JSON.stringify(value));
  window.dispatchEvent(new CustomEvent("codescan:storage-updated", { detail: { key } }));
};

export const removeStored = (key) => {
  localStorage.removeItem(key);
  window.dispatchEvent(new CustomEvent("codescan:storage-updated", { detail: { key } }));
};

export const acquireLock = (key, ttlMs = 3000) => {
  const now = Date.now();
  const existing = Number(localStorage.getItem(key) || 0);
  if (existing && now - existing < ttlMs) {
    return false;
  }
  localStorage.setItem(key, String(now));
  return true;
};

export const releaseLock = (key) => {
  localStorage.removeItem(key);
};
