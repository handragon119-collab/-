"""Threads(Meta) 공식 Graph API 클라이언트.

게시 흐름은 2단계입니다.
1) 미디어 컨테이너 생성 (create container)
2) 컨테이너 게시 (publish)

공식 문서: https://developers.facebook.com/docs/threads
"""

from __future__ import annotations

import time

import requests

GRAPH_BASE = "https://graph.threads.net/v1.0"


class ThreadsError(RuntimeError):
    """Threads API 호출 실패 시 발생하는 예외."""


class ThreadsClient:
    def __init__(self, user_id: str, access_token: str, timeout: int = 30):
        self.user_id = user_id
        self.access_token = access_token
        self.timeout = timeout

    def _post(self, path: str, params: dict) -> dict:
        params = {**params, "access_token": self.access_token}
        resp = requests.post(f"{GRAPH_BASE}/{path}", params=params, timeout=self.timeout)
        if resp.status_code >= 400:
            raise ThreadsError(
                f"Threads API 오류 {resp.status_code}: {resp.text}"
            )
        return resp.json()

    def create_text_container(self, text: str) -> str:
        """텍스트 글 컨테이너를 만들고 creation_id를 반환합니다."""
        data = self._post(
            f"{self.user_id}/threads",
            {"media_type": "TEXT", "text": text},
        )
        creation_id = data.get("id")
        if not creation_id:
            raise ThreadsError(f"creation_id를 받지 못했습니다: {data}")
        return creation_id

    def create_image_container(self, text: str, image_url: str) -> str:
        """이미지 글 컨테이너를 만듭니다. image_url은 공개적으로 접근 가능한 URL이어야 합니다."""
        data = self._post(
            f"{self.user_id}/threads",
            {"media_type": "IMAGE", "image_url": image_url, "text": text},
        )
        creation_id = data.get("id")
        if not creation_id:
            raise ThreadsError(f"creation_id를 받지 못했습니다: {data}")
        return creation_id

    def publish(self, creation_id: str) -> str:
        """컨테이너를 게시하고 게시물 ID를 반환합니다."""
        data = self._post(
            f"{self.user_id}/threads_publish",
            {"creation_id": creation_id},
        )
        post_id = data.get("id")
        if not post_id:
            raise ThreadsError(f"게시물 ID를 받지 못했습니다: {data}")
        return post_id

    def post_text(self, text: str, wait_seconds: int = 3) -> str:
        """텍스트 글을 한 번에 게시합니다. 게시물 ID 반환."""
        creation_id = self.create_text_container(text)
        # 컨테이너가 서버에서 처리될 시간을 잠깐 둡니다(미디어일수록 더 필요).
        time.sleep(wait_seconds)
        return self.publish(creation_id)

    def post_image(self, text: str, image_url: str, wait_seconds: int = 5) -> str:
        """이미지 글을 한 번에 게시합니다. 게시물 ID 반환."""
        creation_id = self.create_image_container(text, image_url)
        time.sleep(wait_seconds)
        return self.publish(creation_id)
