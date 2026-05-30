// JARVIS settings panel — shows live backend health + voice status.
// Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI

interface Health {
  ok: boolean;
  macos: boolean;
  has_anthropic_key: boolean;
  has_elevenlabs_key: boolean;
}

export class Settings {
  private btn: HTMLButtonElement;
  private panel: HTMLElement;
  private open = false;

  constructor() {
    this.btn = document.getElementById("settings-btn") as HTMLButtonElement;
    this.panel = document.getElementById("settings-panel") as HTMLElement;
    this.btn.addEventListener("click", () => this.toggle());
  }

  private async toggle(): Promise<void> {
    this.open = !this.open;
    this.panel.classList.toggle("hidden", !this.open);
    if (this.open) await this.render();
  }

  private async render(): Promise<void> {
    let health: Health | null = null;
    try {
      const res = await fetch("/api/health");
      health = await res.json();
    } catch {
      /* backend unreachable */
    }

    const ok = (b: boolean | undefined) => (b ? "✓" : "✗");
    this.panel.innerHTML = `
      <h3>JARVIS</h3>
      <div class="row"><span>Backend</span><span class="val">${health ? "online" : "offline"}</span></div>
      <div class="row"><span>macOS bridge</span><span class="val">${ok(health?.macos)}</span></div>
      <div class="row"><span>Anthropic key</span><span class="val">${ok(health?.has_anthropic_key)}</span></div>
      <div class="row"><span>ElevenLabs key</span><span class="val">${ok(health?.has_elevenlabs_key)}</span></div>
      <div class="row"><span>Speech input</span><span class="val">${ok(!!(window.SpeechRecognition || (window as any).webkitSpeechRecognition))}</span></div>
    `;
  }
}
