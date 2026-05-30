// JARVIS audio-reactive particle orb (Three.js).
// Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI

import * as THREE from "three";

export type OrbState = "idle" | "listening" | "thinking" | "speaking";

const STATE_COLORS: Record<OrbState, THREE.Color> = {
  idle: new THREE.Color("#4ea3ff"),
  listening: new THREE.Color("#4ea3ff"),
  thinking: new THREE.Color("#ffd166"),
  speaking: new THREE.Color("#06d6a0"),
};

export class Orb {
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private points: THREE.Points;
  private geometry: THREE.BufferGeometry;
  private material: THREE.PointsMaterial;
  private basePositions: Float32Array;
  private count: number;
  private amplitude = 0;
  private targetAmplitude = 0;
  private state: OrbState = "idle";
  private color = STATE_COLORS.idle.clone();
  private targetColor = STATE_COLORS.idle.clone();
  private clock = new THREE.Clock();

  constructor(canvas: HTMLCanvasElement, count = 9000) {
    this.count = count;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(window.innerWidth, window.innerHeight);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(
      55, window.innerWidth / window.innerHeight, 0.1, 100
    );
    this.camera.position.z = 4.2;

    // Distribute points on a fibonacci sphere for an even shell.
    const positions = new Float32Array(count * 3);
    this.basePositions = new Float32Array(count * 3);
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2;
      const radius = Math.sqrt(1 - y * y);
      const theta = golden * i;
      const x = Math.cos(theta) * radius;
      const z = Math.sin(theta) * radius;
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      this.basePositions[i * 3] = x;
      this.basePositions[i * 3 + 1] = y;
      this.basePositions[i * 3 + 2] = z;
    }

    this.geometry = new THREE.BufferGeometry();
    this.geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    this.material = new THREE.PointsMaterial({
      size: 0.018,
      color: this.color,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    this.points = new THREE.Points(this.geometry, this.material);
    this.scene.add(this.points);

    window.addEventListener("resize", () => this.onResize());
    this.animate();
  }

  setState(state: OrbState): void {
    this.state = state;
    this.targetColor = STATE_COLORS[state].clone();
  }

  // value 0..1 from the audio analyser
  setAmplitude(value: number): void {
    this.targetAmplitude = Math.min(1, Math.max(0, value));
  }

  private onResize(): void {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }

  private animate = (): void => {
    requestAnimationFrame(this.animate);
    const t = this.clock.getElapsedTime();

    // Smooth amplitude + color toward targets.
    this.amplitude += (this.targetAmplitude - this.amplitude) * 0.15;
    this.color.lerp(this.targetColor, 0.05);
    this.material.color.copy(this.color);

    const idleBreath = this.state === "idle" ? 0.04 * Math.sin(t * 1.2) : 0;
    const pos = this.geometry.getAttribute("position") as THREE.BufferAttribute;
    const arr = pos.array as Float32Array;

    for (let i = 0; i < this.count; i++) {
      const ix = i * 3;
      const bx = this.basePositions[ix];
      const by = this.basePositions[ix + 1];
      const bz = this.basePositions[ix + 2];
      // Per-point noise driven by audio amplitude.
      const noise =
        Math.sin(bx * 6 + t * 2) * 0.5 +
        Math.cos(by * 6 + t * 1.5) * 0.5;
      const displace = 1 + idleBreath + this.amplitude * 0.45 * (0.5 + 0.5 * noise);
      arr[ix] = bx * displace;
      arr[ix + 1] = by * displace;
      arr[ix + 2] = bz * displace;
    }
    pos.needsUpdate = true;

    this.points.rotation.y += 0.0012 + this.amplitude * 0.004;
    this.points.rotation.x = Math.sin(t * 0.2) * 0.15;
    this.material.size = 0.016 + this.amplitude * 0.02;

    this.renderer.render(this.scene, this.camera);
  };
}
