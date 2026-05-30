// JARVIS voice I/O — Web Speech API recognition + Web Audio playback queue.
// Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI

// Minimal typings for the (still-prefixed) Web Speech API.
interface SpeechRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((ev: any) => void) | null;
  onend: (() => void) | null;
  onerror: ((ev: any) => void) | null;
}
declare global {
  interface Window {
    SpeechRecognition?: { new (): SpeechRecognition };
    webkitSpeechRecognition?: { new (): SpeechRecognition };
  }
}

export class VoiceInput {
  private rec: SpeechRecognition | null = null;
  private wantListening = false;
  private onFinal: (text: string) => void;
  private muted = false;

  constructor(onFinal: (text: string) => void) {
    this.onFinal = onFinal;
    const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (Ctor) {
      this.rec = new Ctor();
      this.rec.lang = "en-GB";
      this.rec.continuous = true;
      this.rec.interimResults = true;
      this.rec.onresult = (ev: any) => {
        for (let i = ev.resultIndex; i < ev.results.length; i++) {
          const r = ev.results[i];
          if (r.isFinal && !this.muted) {
            const text = r[0].transcript.trim();
            if (text) this.onFinal(text);
          }
        }
      };
      this.rec.onend = () => {
        // Chrome stops recognition periodically; restart if we still want it.
        if (this.wantListening) {
          try { this.rec?.start(); } catch { /* already started */ }
        }
      };
      this.rec.onerror = () => { /* swallow; onend handles restart */ };
    }
  }

  get supported(): boolean {
    return this.rec !== null;
  }

  start(): void {
    if (!this.rec) return;
    this.wantListening = true;
    try { this.rec.start(); } catch { /* already running */ }
  }

  stop(): void {
    this.wantListening = false;
    this.rec?.stop();
  }

  // Mute input while JARVIS is speaking, to reduce self-echo.
  setMuted(m: boolean): void {
    this.muted = m;
  }
}

export class AudioPlayer {
  private ctx: AudioContext;
  private queue: ArrayBuffer[] = [];
  private playing = false;
  onAmplitude: ((value: number) => void) | null = null;
  onEnded: (() => void) | null = null;
  private analyser: AnalyserNode;
  private data: Uint8Array<ArrayBuffer>;

  constructor() {
    this.ctx = new AudioContext();
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 256;
    this.analyser.connect(this.ctx.destination);
    this.data = new Uint8Array(new ArrayBuffer(this.analyser.frequencyBinCount));
  }

  resume(): void {
    if (this.ctx.state === "suspended") this.ctx.resume();
  }

  enqueueBase64Mp3(b64: string): void {
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    this.queue.push(bytes.buffer);
    if (!this.playing) void this.playNext();
  }

  private async playNext(): Promise<void> {
    const buf = this.queue.shift();
    if (!buf) {
      this.playing = false;
      this.onEnded?.();
      return;
    }
    this.playing = true;
    try {
      const audioBuf = await this.ctx.decodeAudioData(buf.slice(0));
      const src = this.ctx.createBufferSource();
      src.buffer = audioBuf;
      src.connect(this.analyser);
      src.onended = () => void this.playNext();
      src.start();
      this.pump();
    } catch {
      void this.playNext();
    }
  }

  private pump(): void {
    if (!this.playing) return;
    this.analyser.getByteFrequencyData(this.data);
    let sum = 0;
    for (let i = 0; i < this.data.length; i++) sum += this.data[i];
    const avg = sum / this.data.length / 255; // 0..1
    this.onAmplitude?.(avg);
    requestAnimationFrame(() => this.pump());
  }

  get isPlaying(): boolean {
    return this.playing;
  }
}
