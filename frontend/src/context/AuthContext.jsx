import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import * as authService from "../services/authService";
import { AUTH_STORAGE_KEY } from "../utils/constants";
import { getStoredJson, removeStored, setStoredJson } from "../utils/storage";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [authState, setAuthState] = useState(() => getStoredJson(AUTH_STORAGE_KEY, null));
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const syncAuthState = () => setAuthState(getStoredJson(AUTH_STORAGE_KEY, null));
    window.addEventListener("storage", syncAuthState);
    window.addEventListener("codescan:storage-updated", syncAuthState);

    return () => {
      window.removeEventListener("storage", syncAuthState);
      window.removeEventListener("codescan:storage-updated", syncAuthState);
    };
  }, []);

  const signIn = useCallback(async (credentials) => {
    setLoading(true);
    try {
      const payload = await authService.login(credentials);
      const nextState = {
        user: payload.user,
        accessToken: payload.access_token,
        refreshToken: payload.refresh_token,
      };
      setStoredJson(AUTH_STORAGE_KEY, nextState);
      setAuthState(nextState);
      return nextState;
    } finally {
      setLoading(false);
    }
  }, []);

  const signUp = useCallback(async (input) => {
    setLoading(true);
    try {
      const payload = await authService.signup(input);
      const nextState = {
        user: payload.user,
        accessToken: payload.access_token,
        refreshToken: payload.refresh_token,
      };
      setStoredJson(AUTH_STORAGE_KEY, nextState);
      setAuthState(nextState);
      return nextState;
    } finally {
      setLoading(false);
    }
  }, []);

  const enterGuestMode = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await authService.loginGuest();
      const nextState = {
        user: payload.user,
        accessToken: payload.access_token,
        refreshToken: payload.refresh_token,
      };
      setStoredJson(AUTH_STORAGE_KEY, nextState);
      setAuthState(nextState);
      return nextState;
    } finally {
      setLoading(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    const refreshToken = authState?.refreshToken;
    try {
      await authService.logout(refreshToken);
    } catch {
      // Always clear local session even if server logout fails.
    }
    removeStored(AUTH_STORAGE_KEY);
    setAuthState(null);
  }, [authState?.refreshToken]);

  const value = useMemo(
    () => ({
      user: authState?.user || null,
      accessToken: authState?.accessToken || null,
      refreshToken: authState?.refreshToken || null,
      isAuthenticated: Boolean(authState?.accessToken),
      loading,
      signIn,
      signUp,
      enterGuestMode,
      signOut,
    }),
    [authState, loading, signIn, signOut, signUp, enterGuestMode]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuthContext must be used inside AuthProvider");
  }
  return context;
};
