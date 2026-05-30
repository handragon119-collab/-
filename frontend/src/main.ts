// JARVIS frontend entrypoint — wires orb + voice + websocket into a state machine.
// Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI

import { Orb, type OrbState } from "./orb";
import { JarvisSocket, type ServerMessage } from "./ws";
import { VoiceInput, AudioPlayer } from "./voice";
import { Settings } from "./settings";

const canvas = document.getElementById("orb") as HTMLCanvasElement;
const statusEl = document.getElementById("status") as HTMLElement;
const transcriptEl = document.getElementById("transcript") as HTMLElement;
const overlay = document.getElementById("overlay") as HTMLElement;

const orb = new Orb(canvas);
const player = new AudioPlayer();
new Settings();

let state: OrbState = "idle";

function setState(s: OrbState): void {
  state = s;
  orb.setState(s);
  statusEl.className = `status ${s}`;
  statusEl.textContent = {
    idle: "Listening for you…",
    listening: "Listening…",
    thinking: "Thinking…",
    speaking: "Speaking…",
  }[s];
  // Mute the mic while speaking to avoid self-echo.
  voice.setMuted(s === "speaking" || s === "thinking");
}

function showTranscript(text: string): void {
  transcriptEl.textContent = text;
  transcriptEl.classList.add("show");
  window.clearTimeout((showTranscript as any)._t);
  (showTranscript as any)._t = window.setTimeout(
    () => transcriptEl.classList.remove("show"),
    6000
  );
}

// --- WebSocket ------------------------------------------------------------
const socket = new JarvisSocket((msg: ServerMessage) => {
  switch (msg.type) {
    case "ready":
      setState("idle");
      break;
    case "state":
      setState(msg.state);
      break;
    case "transcript":
      showTranscript(msg.text);
      break;
    case "audio":
      player.enqueueBase64Mp3(msg.data);
      break;
    case "spoken_locally":
      // macOS `say` handled audio; return to idle shortly.
      setTimeout(() => setState("idle"), 800);
      break;
    case "error":
      showTranscript(`⚠ ${msg.message}`);
      setState("idle");
      break;
  }
});

// --- Voice ----------------------------------------------------------------
const voice = new VoiceInput((finalText: string) => {
  if (state === "speaking") return; // ignore while we talk
  showTranscript(finalText);
  socket.sendTranscript(finalText);
});

player.onAmplitude = (v) => orb.setAmplitude(v);
player.onEnded = () => setState("idle");

// --- Boot: require a user gesture to unlock audio + mic -------------------
function boot(): void {
  overlay.classList.add("hidden");
  player.resume();
  socket.connect();
  if (voice.supported) {
    voice.start();
    setState("idle");
  } else {
    statusEl.textContent = "Speech recognition needs Google Chrome.";
  }
}

overlay.addEventListener("click", boot, { once: true });
