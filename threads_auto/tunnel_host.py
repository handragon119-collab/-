"""생성한 이미지를 'cloudflared 터널'로 직접 호스팅합니다.

Imgur 같은 외부 업로드 서비스(키 발급) 없이도, 본인 컴퓨터에서
- 작은 로컬 HTTP 서버로 이미지를 제공하고
- cloudflared 빠른 터널로 인터넷 공개 주소를 만들어
Threads가 가져갈 수 있는 image_url을 제공합니다.

cloudflared가 설치돼 있어야 합니다. (가입·키 불필요)
처음 한 번 터널을 띄우고, 이후 같은 프로세스 동안 재사용합니다.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import threading
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

IMAGE_DIR = Path("data/images")
_TRYCF_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

# 모듈 전역 싱글톤 상태
_lock = threading.Lock()
_public_base: str | None = None
_httpd = None
_cf_proc = None


class TunnelError(RuntimeError):
    """터널/호스팅 실패 시 발생하는 예외."""


def _find_cloudflared() -> str:
    """cloudflared 실행 파일 경로를 찾습니다."""
    found = shutil.which("cloudflared")
    if found:
        return found
    for cand in (
        Path.home() / "bin" / "cloudflared",
        Path("/usr/local/bin/cloudflared"),
        Path("/opt/homebrew/bin/cloudflared"),
    ):
        if cand.exists():
            return str(cand)
    raise TunnelError(
        "cloudflared를 찾을 수 없습니다. 설치했는지 확인하세요 (~/bin/cloudflared)."
    )


def is_available() -> bool:
    """cloudflared가 설치돼 있어 터널 호스팅이 가능한지 여부."""
    try:
        _find_cloudflared()
        return True
    except TunnelError:
        return False


def _start_local_server() -> int:
    """data/images 폴더를 제공하는 로컬 HTTP 서버를 띄우고 포트를 반환합니다."""
    global _httpd
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    directory = str(IMAGE_DIR.resolve())

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, *args):  # 조용히
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    _httpd = httpd
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return port


def _start_tunnel(port: int, timeout: int = 40) -> str:
    """cloudflared 빠른 터널을 띄우고 공개 base URL을 반환합니다."""
    global _cf_proc
    exe = _find_cloudflared()
    proc = subprocess.Popen(
        [exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    _cf_proc = proc

    # 출력에서 trycloudflare.com 주소를 찾을 때까지 읽습니다.
    deadline = time.monotonic() + timeout
    assert proc.stdout is not None
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                raise TunnelError("cloudflared가 예기치 않게 종료됐습니다.")
            continue
        m = _TRYCF_RE.search(line)
        if m:
            return m.group(0)
    raise TunnelError("터널 주소를 시간 내에 받지 못했습니다.")


def get_public_base() -> str:
    """공개 base URL을 반환합니다(없으면 서버+터널을 처음 한 번 띄움)."""
    global _public_base
    with _lock:
        if _public_base:
            return _public_base
        port = _start_local_server()
        _public_base = _start_tunnel(port)
        return _public_base


def host_image(image_bytes: bytes, ext: str = "png") -> str:
    """이미지를 저장하고 공개 URL을 반환합니다. ext로 확장자(jpg/png 등) 지정."""
    base = get_public_base()
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    ext = (ext or "png").lstrip(".").lower()
    if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
        ext = "png"
    name = f"{uuid.uuid4().hex}.{ext}"
    (IMAGE_DIR / name).write_bytes(image_bytes)
    return f"{base}/{name}"
