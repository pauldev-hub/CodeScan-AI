import { useEffect, useRef, useState } from "react";

import { getScanStatus } from "../services/scanService";

const COMPLETE = "complete";
const TERMINAL = ["error", COMPLETE];
const MAX_BACKOFF_MS = 12000;

export const useScanStatus = (scanId, options = {}) => {
  const {
    enabled = true,
    pollMs = 2500,
    maxAttempts = 200,
    maxDurationMs = 8 * 60 * 1000,
    onComplete,
  } = options;

  const [statusState, setStatusState] = useState({
    status: "pending",
    progress: 0,
    error: null,
    timedOut: false,
    attempts: 0,
  });

  const attempts = useRef(0);
  const failureCount = useRef(0);
  const timerRef = useRef(null);
  const startedAtRef = useRef(0);

  useEffect(() => {
    if (!enabled || !scanId) {
      return;
    }

    attempts.current = 0;
    failureCount.current = 0;
    startedAtRef.current = Date.now();

    let cancelled = false;

    const scheduleNext = (delay) => {
      timerRef.current = setTimeout(poll, delay);
    };

    const getRetryDelay = () => {
      const multiplier = 2 ** Math.min(failureCount.current, 3);
      return Math.min(pollMs * multiplier, MAX_BACKOFF_MS);
    };

    const poll = async () => {
      attempts.current += 1;
      const elapsed = Date.now() - startedAtRef.current;

      if (elapsed >= maxDurationMs || attempts.current > maxAttempts) {
        setStatusState((prev) => ({
          ...prev,
          status: "error",
          timedOut: true,
          error: {
            message: "Scan polling timed out. You can reopen the results page later.",
          },
          attempts: attempts.current,
        }));
        return;
      }

      const controller = new AbortController();

      try {
        const payload = await getScanStatus(scanId, controller.signal);
        if (cancelled) {
          return;
        }
        failureCount.current = 0;
        setStatusState({
          status: payload.status || "pending",
          progress: payload.progress || 0,
          error: null,
          timedOut: false,
          attempts: attempts.current,
        });

        if (payload.status === COMPLETE && onComplete) {
          onComplete(payload);
        }

        if (TERMINAL.includes(payload.status) || attempts.current >= maxAttempts) {
          return;
        }
      } catch (error) {
        if (cancelled) {
          return;
        }
        failureCount.current += 1;
        setStatusState((prev) => ({ ...prev, error, attempts: attempts.current }));
      }

      scheduleNext(getRetryDelay());
    };

    poll();

    return () => {
      cancelled = true;
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [enabled, maxAttempts, maxDurationMs, onComplete, pollMs, scanId]);

  return statusState;
};
