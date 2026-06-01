"""동영상에서 대표 프레임 몇 장을 뽑아냅니다(영상 분석용).

Claude는 동영상을 직접 받지 못하므로, 영상에서 고르게 프레임을 추출해
이미지로 분석합니다. opencv가 있으면 사용하고, 없으면 친절히 안내합니다.
"""

from __future__ import annotations


class VideoError(RuntimeError):
    pass


def extract_frames(path: str, max_frames: int = 5) -> list[bytes]:
    """영상에서 균등 간격으로 최대 max_frames장의 JPEG 프레임(bytes)을 추출."""
    try:
        import cv2  # opencv-python-headless
    except Exception as exc:  # noqa: BLE001
        raise VideoError(
            "동영상 분석에 필요한 opencv가 설치되지 않았습니다. "
            "터미널에서 'pip3 install opencv-python-headless' 후 다시 시도하세요."
        ) from exc

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise VideoError("영상을 열 수 없습니다.")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    frames: list[bytes] = []
    try:
        if total > 0:
            step = max(total // max_frames, 1)
            idxs = list(range(0, total, step))[:max_frames]
            for i in idxs:
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ok, frame = cap.read()
                if not ok:
                    continue
                ok2, buf = cv2.imencode(".jpg", frame)
                if ok2:
                    frames.append(buf.tobytes())
        else:
            # 프레임 수를 모를 때: 순차로 읽으며 일부만
            count = 0
            while len(frames) < max_frames and count < 3000:
                ok, frame = cap.read()
                if not ok:
                    break
                if count % 30 == 0:  # 약 1초 간격(30fps 가정)
                    ok2, buf = cv2.imencode(".jpg", frame)
                    if ok2:
                        frames.append(buf.tobytes())
                count += 1
    finally:
        cap.release()

    if not frames:
        raise VideoError("영상에서 프레임을 추출하지 못했습니다.")
    return frames
