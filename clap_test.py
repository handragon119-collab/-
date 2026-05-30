#!/usr/bin/env python3
"""
clap_test.py - 마이크 / 박수 감지 진단 도구.

실행:  python clap_test.py
그리고 박수를 쳐보세요. 마이크가 정상이면 막대그래프가 출렁이고,
박수를 치면 'CLAP!' 이 떠야 합니다.

- 막대가 전혀 안 움직이면  → 마이크 권한 또는 장치 문제 (특히 macOS)
- 박수에만 'CLAP!' 이 뜨면 → 정상. 이 임계값을 그대로 쓰면 됩니다.
"""
import sys

try:
    import pyaudio  # type: ignore
except Exception as exc:
    print("❌ PyAudio가 설치되지 않았습니다. 박수 감지를 쓰려면 필요합니다.")
    print(f"   ({exc})")
    print("\nmacOS 설치:")
    print("   brew install portaudio")
    print("   pip install pyaudio")
    sys.exit(1)

import array
import math


def rms(frame: bytes) -> float:
    s = array.array("h")
    s.frombytes(frame)
    return math.sqrt(sum(x * x for x in s) / len(s)) if s else 0.0


CHUNK, RATE = 1024, 16000

pa = pyaudio.PyAudio()

# 입력 장치 목록 표시
print("=" * 60)
print("🎙  사용 가능한 입력(마이크) 장치:")
default_in = None
try:
    default_in = pa.get_default_input_device_info().get("index")
except Exception:
    pass
for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    if info.get("maxInputChannels", 0) > 0:
        mark = "  ← 기본" if i == default_in else ""
        print(f"   [{i}] {info.get('name')}{mark}")
print("=" * 60)

try:
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)
except Exception as exc:
    print(f"❌ 마이크 스트림을 열 수 없습니다: {exc}")
    print("   → macOS라면 시스템 설정 → 개인정보 보호 및 보안 → 마이크 에서")
    print("     '터미널'(또는 iTerm)을 켜주세요.")
    sys.exit(1)

# 0.5초 보정
print("⏳ 주변 소음 측정 중... (조용히 0.5초)")
levels = [rms(stream.read(CHUNK, exception_on_overflow=False)) for _ in range(8)]
ambient = sum(levels) / len(levels)
threshold = max(ambient * 6.0, 2000.0)
print(f"   주변 소음 평균: {ambient:7.0f}   |   박수 임계값: {threshold:7.0f}")

if ambient == 0:
    print("\n⚠️  마이크 음량이 계속 0입니다 → 소리가 전혀 안 들어옵니다.")
    print("   macOS: 시스템 설정 → 개인정보 보호 및 보안 → 마이크 에서")
    print("   터미널 앱의 권한을 켜고 터미널을 완전히 종료 후 다시 실행하세요.")

print("\n👏 이제 박수를 쳐보세요! (Ctrl+C 로 종료)\n")
clap_count = 0
try:
    quiet = True
    while True:
        level = rms(stream.read(CHUNK, exception_on_overflow=False))
        bar = "█" * min(int(level / 400), 50)
        flag = ""
        if level < threshold * 0.4:
            quiet = True
        elif level > threshold and quiet:
            clap_count += 1
            quiet = False
            flag = f"   👏 CLAP! (#{clap_count})"
        print(f"\r음량 {level:6.0f} |{bar:<50}|{flag}", end="", flush=True)
except KeyboardInterrupt:
    print(f"\n\n총 {clap_count}번의 박수를 감지했습니다. 진단 종료.")
finally:
    stream.stop_stream()
    stream.close()
    pa.terminate()
