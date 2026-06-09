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

    def get_profile(self) -> dict:
        """내 프로필(아이디·사진 등)을 가져옵니다."""
        params = {
            "fields": "id,username,threads_profile_picture_url,name",
            "access_token": self.access_token,
        }
        resp = requests.get(f"{GRAPH_BASE}/me", params=params, timeout=self.timeout)
        if resp.status_code >= 400:
            raise ThreadsError(f"프로필 조회 실패 {resp.status_code}: {resp.text}")
        return resp.json()

    def _get(self, path: str, params: dict) -> dict:
        params = {**params, "access_token": self.access_token}
        resp = requests.get(f"{GRAPH_BASE}/{path}", params=params, timeout=self.timeout)
        if resp.status_code >= 400:
            raise ThreadsError(f"Threads API 오류 {resp.status_code}: {resp.text}")
        return resp.json()

    def get_my_posts(self, limit: int = 25) -> list[dict]:
        """내 최근 게시물 목록(페이지 넘기며 모음)."""
        out: list[dict] = []
        data = self._get(f"{self.user_id}/threads",
                         {"fields": "id,text,timestamp,media_type,permalink", "limit": 50})
        out += data.get("data", [])
        nxt = (data.get("paging") or {}).get("next")
        pages = 1
        while nxt and len(out) < limit and pages < 6:
            try:
                resp = requests.get(nxt, timeout=self.timeout)
                j = resp.json()
            except Exception:  # noqa: BLE001
                break
            out += j.get("data", [])
            nxt = (j.get("paging") or {}).get("next")
            pages += 1
        return out[:limit] if limit else out

    def get_replies(self, media_id: str, max_pages: int = 12) -> list[dict]:
        """특정 게시물에 달린 답글(댓글) 전부 — 페이지를 넘기며 모읍니다."""
        out: list[dict] = []
        data = self._get(f"{media_id}/replies",
                         {"fields": "id,text,username,timestamp", "limit": 100})
        out += data.get("data", [])
        nxt = (data.get("paging") or {}).get("next")
        pages = 1
        while nxt and pages < max_pages:
            try:
                resp = requests.get(nxt, timeout=self.timeout)
                j = resp.json()
            except Exception:  # noqa: BLE001
                break
            out += j.get("data", [])
            nxt = (j.get("paging") or {}).get("next")
            pages += 1
        return out

    def get_post_insights(self, media_id: str) -> dict:
        """게시물 인사이트(조회수·좋아요·댓글·리포스트 등).

        토큰에 'threads_manage_insights' 권한이 필요합니다.
        반환 예: {"views": 1234, "likes": 56, "replies": 7, "reposts": 2, "quotes": 0, "shares": 1}
        """
        params = {
            "metric": "views,likes,replies,reposts,quotes,shares",
            "access_token": self.access_token,
        }
        resp = requests.get(
            f"{GRAPH_BASE}/{media_id}/insights", params=params, timeout=self.timeout
        )
        if resp.status_code >= 400:
            raise ThreadsError(f"인사이트 조회 실패 {resp.status_code}: {resp.text}")
        out: dict = {}
        for m in resp.json().get("data", []):
            name = m.get("name")
            val = None
            tv = m.get("total_value")
            if isinstance(tv, dict):
                val = tv.get("value")
            if val is None:
                vals = m.get("values") or []
                if vals:
                    val = vals[0].get("value")
            out[name] = val or 0
        return out

    def get_user_insights(self, metrics: str = "views") -> dict:
        """계정 단위 인사이트(예: 최근 조회수, 팔로워 수). 권한 필요."""
        params = {"metric": metrics, "access_token": self.access_token}
        resp = requests.get(
            f"{GRAPH_BASE}/{self.user_id}/threads_insights", params=params,
            timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise ThreadsError(f"계정 인사이트 조회 실패 {resp.status_code}: {resp.text}")
        out: dict = {}
        for m in resp.json().get("data", []):
            name = m.get("name")
            tv = m.get("total_value")
            if isinstance(tv, dict):
                out[name] = tv.get("value", 0)
            else:
                vals = m.get("values") or []
                out[name] = vals[-1].get("value", 0) if vals else 0
        return out

    def like(self, media_id: str) -> None:
        """댓글/게시물에 좋아요. (Threads 공식 API가 아직 미지원 → 시도만, 실패 시 예외)"""
        # Threads Graph API에는 공개 like 엔드포인트가 없음. 추후 추가될 경우를 대비한 시도.
        self._post(f"{media_id}/likes", {})

    def post_reply(self, text: str, reply_to_id: str, wait_seconds: int = 3) -> str:
        """특정 댓글/게시물에 답글을 답니다. 게시물 ID 반환."""
        data = self._post(
            f"{self.user_id}/threads",
            {"media_type": "TEXT", "text": text, "reply_to_id": reply_to_id},
        )
        creation_id = data.get("id")
        if not creation_id:
            raise ThreadsError(f"답글 컨테이너 생성 실패: {data}")
        time.sleep(wait_seconds)
        return self.publish(creation_id)

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

    # ── 캐러셀(사진 여러 장) ──
    def create_carousel_item(self, image_url: str) -> str:
        """캐러셀에 들어갈 이미지 아이템 컨테이너를 만듭니다."""
        data = self._post(
            f"{self.user_id}/threads",
            {"media_type": "IMAGE", "image_url": image_url, "is_carousel_item": "true"},
        )
        item_id = data.get("id")
        if not item_id:
            raise ThreadsError(f"캐러셀 아이템 생성 실패: {data}")
        return item_id

    def post_carousel(self, text: str, image_urls: list[str], wait_seconds: int = 5) -> str:
        """사진 여러 장을 캐러셀로 게시합니다. (2~20장)"""
        children = [self.create_carousel_item(u) for u in image_urls]
        time.sleep(wait_seconds)
        data = self._post(
            f"{self.user_id}/threads",
            {"media_type": "CAROUSEL", "children": ",".join(children), "text": text},
        )
        creation_id = data.get("id")
        if not creation_id:
            raise ThreadsError(f"캐러셀 컨테이너 생성 실패: {data}")
        time.sleep(wait_seconds)
        return self.publish(creation_id)

    # ── 동영상 ──
    def _container_status(self, creation_id: str) -> str:
        params = {"fields": "status", "access_token": self.access_token}
        resp = requests.get(
            f"{GRAPH_BASE}/{creation_id}", params=params, timeout=self.timeout
        )
        if resp.status_code >= 400:
            return "ERROR"
        return resp.json().get("status", "")

    def post_video(self, text: str, video_url: str, max_wait: int = 120) -> str:
        """동영상 글을 게시합니다. 영상 처리가 끝날 때까지 기다린 뒤 게시."""
        data = self._post(
            f"{self.user_id}/threads",
            {"media_type": "VIDEO", "video_url": video_url, "text": text},
        )
        creation_id = data.get("id")
        if not creation_id:
            raise ThreadsError(f"비디오 컨테이너 생성 실패: {data}")
        # 영상은 서버 처리 시간이 필요 → FINISHED 될 때까지 폴링
        waited = 0
        while waited < max_wait:
            status = self._container_status(creation_id)
            if status == "FINISHED":
                break
            if status == "ERROR":
                raise ThreadsError("영상 처리 중 오류가 발생했습니다.")
            time.sleep(5)
            waited += 5
        return self.publish(creation_id)

    def post_media(self, text: str, image_urls: list[str] | None = None,
                   video_url: str | None = None) -> str:
        """미디어 종류에 맞춰 게시합니다(자동 분기)."""
        if video_url:
            return self.post_video(text, video_url)
        urls = image_urls or []
        if len(urls) >= 2:
            return self.post_carousel(text, urls)
        if len(urls) == 1:
            return self.post_image(text, urls[0])
        return self.post_text(text)
