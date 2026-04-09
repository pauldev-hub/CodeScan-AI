import { useEffect, useState } from "react";

import { BEGINNER_MODE_STORAGE_KEY } from "../utils/constants";

export const useBeginnerMode = () => {
  const [enabled, setEnabled] = useState(() => localStorage.getItem(BEGINNER_MODE_STORAGE_KEY) !== "false");

  useEffect(() => {
    localStorage.setItem(BEGINNER_MODE_STORAGE_KEY, enabled ? "true" : "false");
  }, [enabled]);

  return {
    beginnerMode: enabled,
    setBeginnerMode: setEnabled,
    toggleBeginnerMode: () => setEnabled((current) => !current),
  };
};
