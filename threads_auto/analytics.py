"""내 게시물 성과(조회수·좋아요·댓글)를 가져와 분석합니다.

Threads 공식 인사이트 API를 사용합니다(토큰에 threads_manage_insights 권한 필요).
- 글마다 조회수/좋아요/댓글/리포스트를 모아서
- 조회수 추세(최근 vs 이전), 잘 된 글/안 된 글, 잘 되는 시간대를 계산하고
- (Claude API가 있으면) 강아지 계정 맥락에 맞춘 진단 + 해결방안을 글로 만들어 줍니다.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def _parse_dt(ts: str | None):
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(ts, fmt).astimezone(KST)
        except ValueError:
            continue
    return None


def _avg(nums: list[float]) -> float:
    nums = [n for n in nums if n is not None]
    return sum(nums) / len(nums) if nums else 0.0


def collect(acc: dict, limit: int = 25, on_progress=None) -> dict:
    """계정의 최근 글 + 인사이트를 모읍니다. {rows, insights_ok, error}"""
    from threads_auto.threads_client import ThreadsClient

    client = ThreadsClient(acc["user_id"], acc["access_token"])
    posts = client.get_my_posts(limit)
    rows: list[dict] = []
    insights_ok = True
    first_error = ""
    total = len(posts)
    for i, p in enumerate(posts):
        ins: dict = {}
        try:
            ins = client.get_post_insights(p["id"])
        except Exception as exc:  # noqa: BLE001
            insights_ok = False
            if not first_error:
                first_error = str(exc)
        dt = _parse_dt(p.get("timestamp"))
        rows.append({
            "id": p.get("id"),
            "text": (p.get("text") or "").strip(),
            "media_type": p.get("media_type", ""),
            "permalink": p.get("permalink", ""),
            "dt": dt,
            "ts": p.get("timestamp"),
            "views": int(ins.get("views", 0) or 0),
            "likes": int(ins.get("likes", 0) or 0),
            "replies": int(ins.get("replies", 0) or 0),
            "reposts": int(ins.get("reposts", 0) or 0),
        })
        if on_progress:
            on_progress(i + 1, total)
    return {"rows": rows, "insights_ok": insights_ok, "error": first_error}


def analyze(acc: dict, limit: int = 25, on_progress=None,
            anthropic_key: str = "", model: str = "", learn: bool = True) -> dict:
    """성과를 분석해 요약·추세·베스트/워스트·시간대·진단을 반환합니다.

    learn=True이면 '실제로 조회수 잘 나온 글'을 그 계정 학습 예시로 저장하고,
    잘 나오는 시간대 등을 조회수 전략 노트에 반영한다(다음 글 생성에 즉시 적용).
    """
    data = collect(acc, limit=limit, on_progress=on_progress)
    rows = data["rows"]
    if not rows:
        return {"ok": False, "error": "게시물이 없어요.", "insights_ok": data["insights_ok"]}

    # 인사이트 권한이 없으면 숫자가 전부 0 → 안내만 반환
    has_views = any(r["views"] for r in rows)
    if not data["insights_ok"] and not has_views:
        return {
            "ok": False, "insights_ok": False,
            "error": data["error"] or "인사이트 권한이 없어요.",
            "need_permission": True,
        }

    # 최신순 정렬(보통 API가 최신순이지만 확실히)
    rows.sort(key=lambda r: r["dt"] or datetime.min.replace(tzinfo=KST), reverse=True)

    # 추세: 최근 절반 vs 이전 절반 평균 조회수
    half = max(1, len(rows) // 2)
    recent = rows[:half]
    older = rows[half:] or rows[:half]
    recent_avg = _avg([r["views"] for r in recent])
    older_avg = _avg([r["views"] for r in older])
    trend_pct = ((recent_avg - older_avg) / older_avg * 100) if older_avg else 0.0

    # 참여율(조회 대비 좋아요+댓글+리포스트)
    def eng(r):
        return (r["likes"] + r["replies"] + r["reposts"]) / r["views"] if r["views"] else 0.0

    ranked = sorted(rows, key=lambda r: r["views"], reverse=True)
    top = ranked[:3]
    worst = [r for r in ranked if r["views"]][-3:][::-1]

    # 시간대별 평균 조회수
    by_hour: dict[int, list[int]] = {}
    by_wday: dict[int, list[int]] = {}
    for r in rows:
        if r["dt"]:
            by_hour.setdefault(r["dt"].hour, []).append(r["views"])
            by_wday.setdefault(r["dt"].weekday(), []).append(r["views"])
    best_hours = sorted(
        ((h, _avg(v)) for h, v in by_hour.items() if v), key=lambda x: x[1], reverse=True
    )[:3]
    best_wdays = sorted(
        ((d, _avg(v)) for d, v in by_wday.items() if v), key=lambda x: x[1], reverse=True
    )[:2]

    def slim(r):
        return {
            "text": r["text"][:80], "views": r["views"], "likes": r["likes"],
            "replies": r["replies"], "reposts": r["reposts"],
            "eng": round(eng(r) * 100, 1),
            "when": r["dt"].strftime("%m/%d %H시") if r["dt"] else "",
            "media_type": r["media_type"],
        }

    summary = {
        "count": len(rows),
        "avg_views": round(_avg([r["views"] for r in rows])),
        "recent_avg": round(recent_avg),
        "older_avg": round(older_avg),
        "trend_pct": round(trend_pct, 1),
        "avg_likes": round(_avg([r["likes"] for r in rows]), 1),
        "avg_replies": round(_avg([r["replies"] for r in rows]), 1),
        "avg_eng": round(_avg([eng(r) for r in rows]) * 100, 1),
        "top": [slim(r) for r in top],
        "worst": [slim(r) for r in worst],
        "best_hours": [{"hour": h, "avg": round(a)} for h, a in best_hours],
        "best_wdays": [{"day": WEEKDAYS[d], "avg": round(a)} for d, a in best_wdays],
        "series": [
            {"when": r["dt"].strftime("%m/%d") if r["dt"] else "", "views": r["views"]}
            for r in rows[:14][::-1]
        ],
        "insights_ok": data["insights_ok"],
    }

    diagnosis = ""
    if anthropic_key:
        try:
            diagnosis = _llm_diagnosis(acc, summary, anthropic_key, model)
        except Exception:  # noqa: BLE001
            diagnosis = ""

    learned = None
    if learn:
        try:
            learned = _learn_winners(acc, rows, summary)
        except Exception:  # noqa: BLE001
            learned = None

    return {"ok": True, "insights_ok": data["insights_ok"],
            "summary": summary, "diagnosis": diagnosis, "learned": learned}


def _learn_winners(acc: dict, rows: list[dict], summary: dict) -> dict:
    """실제로 조회수 잘 나온 글을 학습 예시로 저장 + 조회수 전략 노트 갱신.

    - '잘 나온 글' = 조회수가 (전체 평균과 최근 평균 중 큰 값) 이상인 글들, 최대 6개.
      → 이 계정의 학습 예시로 등록해 다음 생성이 '검증된 승자'를 닮게 한다.
    - 잘 나오는 시간대 + 추세 + 승자 글 첫 줄을 전략 노트로 저장.
    """
    from threads_auto import samples, strategy

    acc_id = acc.get("id")
    if not acc_id:
        return {"samples": 0}

    ranked_by_views = [r for r in sorted(rows, key=lambda r: r["views"], reverse=True)
                       if r["views"]]
    bar = max(summary.get("avg_views", 0), summary.get("recent_avg", 0))
    winners = [r for r in ranked_by_views if r["views"] >= bar][:6]
    # 기준이 너무 빡세 1~2개만 잡히면, 그냥 상위 글로 최소 3개는 학습
    if len(winners) < 3:
        for r in ranked_by_views[:3]:
            if r not in winners:
                winners.append(r)

    n = 0
    for r in winners:
        txt = (r.get("text") or "").strip()
        if len(txt) >= 8:
            samples.add_sample(acc_id, txt)
            n += 1

    # 승자 글들의 첫 줄(후킹)만 모아 전략 노트에 박아둠
    hooks = []
    for r in winners[:3]:
        first = (r.get("text") or "").strip().splitlines()[0] if r.get("text") else ""
        if first:
            hooks.append(first[:40])
    best_hours = [h["hour"] for h in summary.get("best_hours", [])]

    note_lines = [
        f"최근 평균 조회수 {summary.get('recent_avg', 0)} "
        f"(추세 {summary.get('trend_pct', 0):+}%). 조회수가 떨어지는 중이면 "
        "아래 '실제로 잘 나온 글'의 첫 줄 후킹·길이·주제 방향을 적극적으로 닮아라.",
    ]
    if hooks:
        note_lines.append("실제로 조회 잘 나온 글의 첫 줄 예: " + " / ".join(f'"{h}"' for h in hooks))
    strategy.set_note(acc_id, "\n".join(note_lines), best_hours)

    return {"samples": n, "best_hours": best_hours, "winners": len(winners)}


def _llm_diagnosis(acc: dict, summary: dict, anthropic_key: str, model: str) -> str:
    """실제 수치를 바탕으로 강아지 계정 맥락의 진단+해결방안을 한국어로 생성."""
    import anthropic

    persona = acc.get("persona", "general")
    persona_kr = {"pet": "강아지 1인칭 반려동물", "studio": "사진관 사장님",
                  "founder": "대표/크리에이터"}.get(persona, "일반")
    top_txt = "\n".join(
        f"- 조회 {t['views']} / 좋아요 {t['likes']} / 댓글 {t['replies']} "
        f"({t['when']}, {t['media_type'] or '글'}): {t['text']}"
        for t in summary["top"]
    )
    worst_txt = "\n".join(
        f"- 조회 {t['views']} / 좋아요 {t['likes']} ({t['when']}): {t['text']}"
        for t in summary["worst"]
    )
    hours = ", ".join(f"{h['hour']}시(평균 {h['avg']})" for h in summary["best_hours"])
    prompt = (
        f"너는 한국 Threads(스레드) 성장 컨설턴트다. 아래는 '{persona_kr}' 계정의 최근 "
        f"{summary['count']}개 글 실제 성과 데이터다.\n\n"
        f"평균 조회수: {summary['avg_views']}\n"
        f"최근 절반 평균: {summary['recent_avg']} / 이전 절반 평균: {summary['older_avg']} "
        f"(추세 {summary['trend_pct']:+}%)\n"
        f"평균 좋아요: {summary['avg_likes']}, 평균 댓글: {summary['avg_replies']}, "
        f"평균 참여율: {summary['avg_eng']}%\n"
        f"조회 잘 나온 시간대: {hours}\n\n"
        f"[잘 된 글]\n{top_txt}\n\n[안 된 글]\n{worst_txt}\n\n"
        "이 데이터를 근거로 다음을 한국어로, 친근한 반말로, 군더더기 없이 써줘:\n"
        "1) 조회수가 왜 이런지 '데이터에서 드러난' 진단 2~3가지 (구체 수치 인용)\n"
        "2) 이번 주에 당장 실행할 해결방안 3~5가지 (실천 가능하게, 강아지 계정 맥락)\n"
        "3) 다음에 올리면 잘 될 것 같은 글 아이디어 2개\n"
        "이모지는 적게. 마크다운 제목(#) 대신 '1) 2)' 번호로. 짧고 명확하게."
    )
    client = anthropic.Anthropic(api_key=anthropic_key)
    resp = client.messages.create(
        model=model, max_tokens=1500, thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()
