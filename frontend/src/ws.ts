// JARVIS WebSocket client with auto-reconnect.
// Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI

export type ServerMessage =
  | { type: "ready"; session: string; user?: string }
  | { type: "state"; state: "idle" | "listening" | "thinking" | "speaking" }
  | { type: "transcript"; role: "assistant" | "user"; text: string }
  | { type: "audio"; format: "mp3"; data: string }
  | { type: "spoken_locally"; engine: string }
  | { type: "error"; message: string }
  | { type: "pong" };

type Handler = (msg: ServerMessage) => void;

export class JarvisSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private handler: Handler;
  private reconnectDelay = 1000;
  private closed = false;
  private pingTimer: number | null = null;

  constructor(handler: Handler) {
    this.handler = handler;
    // Vite proxies /ws → backend; in a built app this hits the same origin.
    const proto = location.protocol === "https:" ? "wss" : "ws";
    this.url = `${proto}://${location.host}/ws/voice`;
  }

  connect(): void {
    this.closed = false;
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.startPing();
    };

    this.ws.onmessage = (ev) => {
      try {
        this.handler(JSON.parse(ev.data) as ServerMessage);
      } catch {
        /* ignore malformed frames */
      }
    };

    this.ws.onclose = () => {
      this.stopPing();
      if (!this.closed) {
        setTimeout(() => this.connect(), this.reconnectDelay);
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 15000);
      }
    };

    this.ws.onerror = () => this.ws?.close();
  }

  send(msg: Record<string, unknown>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  sendTranscript(text: string): void {
    this.send({ type: "transcript", text });
  }

  private startPing(): void {
    this.pingTimer = window.setInterval(() => this.send({ type: "ping" }), 20000);
  }

  private stopPing(): void {
    if (this.pingTimer !== null) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  close(): void {
    this.closed = true;
    this.stopPing();
    this.ws?.close();
  }
}
