import { useState, useEffect, useRef } from "react";
import type { LogEntry } from "@/types/ui";
import { SSE_STREAM_URL } from "@/api/logs";

const MAX_BUFFER = 1000;

interface UseSseLogOptions {
  enabled?: boolean;
  startAfterTimestamp?: string;
}

interface UseSseLogResult {
  entries: LogEntry[];
  isConnected: boolean;
  isError: boolean;
}

export function useSseLog({ enabled = true, startAfterTimestamp }: UseSseLogOptions = {}): UseSseLogResult {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isError, setIsError] = useState(false);
  const cutoff = useRef<string>(startAfterTimestamp ?? new Date().toISOString());

  useEffect(() => {
    if (startAfterTimestamp) {
      cutoff.current = startAfterTimestamp;
    }
  }, [startAfterTimestamp]);

  useEffect(() => {
    if (!enabled) {
      setIsConnected(false);
      return;
    }

    const es = new EventSource(SSE_STREAM_URL, { withCredentials: true });

    es.onopen = () => {
      setIsConnected(true);
      setIsError(false);
    };

    es.onmessage = (event: MessageEvent) => {
      try {
        const entry: LogEntry = JSON.parse(event.data as string);
        // Only add entries newer than the cutoff (avoids duplicates)
        if (entry.timestamp > cutoff.current) {
          setEntries(prev => [...prev.slice(-(MAX_BUFFER - 1)), entry]);
          // Update the cutoff to prevent duplicates on automatic EventSource reconnects
          cutoff.current = entry.timestamp;
        }
      } catch {
        // ignore malformed SSE lines
      }
    };

    es.onerror = () => {
      setIsConnected(false);
      setIsError(true);
    };

    return () => {
      es.close();
    };
  }, [enabled]);

  return { entries, isConnected, isError };
}
