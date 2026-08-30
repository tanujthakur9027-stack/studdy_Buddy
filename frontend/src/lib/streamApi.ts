/**
 * streamApi.ts — Streaming SSE helpers for LLM endpoints.
 *
 * Protocol (matches the backend):
 *   data: <token>          → raw text token, newlines escaped as \\n
 *   data: [SOURCES]<json>  → final metadata object (sources, mode_used, etc.)
 *   data: [DONE]           → stream complete
 *   data: [ERROR] <msg>    → server-side error
 */

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface StreamMeta {
  sources?: Array<{ filename: string; page: number; chunk_index: number; snippet: string }>;
  sourceNames?: string[];        // doubt/stream returns string array
  context_chunks_used?: number;
  mode_used?: string;
}

export interface StreamCallbacks {
  /** Called with each decoded token string */
  onToken: (_token: string) => void;
  /** Called once when the stream finishes, with optional metadata */
  onDone?: (_meta: StreamMeta) => void;
  /** Called if there's an error mid-stream */
  onError?: (_msg: string) => void;
}

/**
 * POST to a streaming endpoint and drive the callbacks.
 * Returns an AbortController so the caller can cancel.
 */
export function streamPost(
  path: string,
  body: Record<string, unknown>,
  callbacks: StreamCallbacks,
): AbortController {
  const controller = new AbortController();

  (async () => {
    let response: Response;
    try {
      response = await fetch(`${BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        callbacks.onError?.(`Network error: ${(e as Error).message}`);
      }
      return;
    }

    if (!response.ok) {
      const text = await response.text().catch(() => "Unknown error");
      callbacks.onError?.(`HTTP ${response.status}: ${text}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) { callbacks.onError?.("No response body"); return; }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      let done: boolean, value: Uint8Array | undefined;
      try {
        ({ done, value } = await reader.read());
      } catch {
        // Cancelled by AbortController — silent exit
        return;
      }
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE lines end with \n\n
      const lines = buffer.split("\n\n");
      buffer = lines.pop() ?? "";   // keep incomplete last chunk

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);  // strip "data: "

        if (payload === "[DONE]") {
          callbacks.onDone?.({});
          return;
        }

        if (payload.startsWith("[ERROR]")) {
          callbacks.onError?.(payload.slice(7).trim());
          return;
        }

        if (payload.startsWith("[SOURCES]")) {
          try {
            const meta: StreamMeta = JSON.parse(payload.slice(9));
            callbacks.onDone?.(meta);
          } catch {
            callbacks.onDone?.({});
          }
          return;
        }

        // Regular token — unescape newlines
        const token = payload.replace(/\\n/g, "\n");
        callbacks.onToken(token);
      }
    }

    callbacks.onDone?.({});
  })();

  return controller;
}
