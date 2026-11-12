"""Turn the API responses into the compact shape the Scriptable widget draws.

Keep the field names in sync with summarize() in the widget script.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _deadline(m: dict) -> datetime:
    value = m.get("earliest_report_deadline") or m.get("deadline")
    if not value:
        return datetime.fromtimestamp(0, timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _tests_done(m: dict) -> bool:
    return (m.get("passed_assessment_test_count") or 0) >= (m.get("total_assessment_test") or 0)


def _is_done(m: dict) -> bool:
    return m["passed_chapter_count"] >= m["total_chapter_count"] and _tests_done(m)


def _sorted(summaries: list[dict]) -> list[dict]:
    return sorted(summaries, key=lambda m: (m["year"], m["month"]))


def pick_month(summaries: list[dict], now: datetime) -> dict | None:
    ordered = _sorted(summaries)
    if not ordered:
        return None
    open_months = [m for m in ordered if _deadline(m) >= now]
    return next((m for m in open_months if not _is_done(m)), None) or \
        (open_months[0] if open_months else ordered[-1])


def _iso(dt: datetime) -> str:
    # Seconds only: iOS JavaScript may reject microsecond fractions.
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _month(m: dict | None) -> dict | None:
    if not m:
        return None
    return {
        "year": m["year"], "month": m["month"], "deadline": _iso(_deadline(m)),
        "chaptersPassed": m["passed_chapter_count"], "chaptersTotal": m["total_chapter_count"],
        "testsPassed": m.get("passed_assessment_test_count") or 0,
        "testsTotal": m.get("total_assessment_test") or 0,
    }


def summarize(overview: dict, detail: dict | None, now: datetime) -> dict:
    summaries = overview.get("monthly_summaries") or []
    if not summaries:
        raise ValueError("レポートがありません")
    ordered = _sorted(summaries)
    current = pick_month(summaries, now)
    index = ordered.index(current)
    following = ordered[index + 1] if index + 1 < len(ordered) else None
    detail = detail or {}
    passed_tests = {t.get("assessment_test_id") for t in detail.get("passed_assessment_tests") or []}
    groups = detail.get("deadline_groups") or []
    remaining = sorted(
        ({"subject": c.get("subject_category_title") or c.get("course_title"),
          "title": c.get("chapter_title"),
          "passed": c["passed_count"], "total": c["total_count"]}
         for g in groups for c in g.get("chapters") or []
         if not c.get("exempted") and c["passed_count"] < c["total_count"]),
        key=lambda c: c["total"] - c["passed"])
    tests = [{"subject": t.get("subject_category_title") or t.get("course_title"), "title": t.get("title"),
              "answered": t.get("total_answered_question") or 0, "total": t.get("total_question") or 0}
             for g in groups for t in g.get("assessment_tests") or []
             if not t.get("exempted") and t.get("assessment_test_id") not in passed_tests]
    current_out = _month(current)
    current_out["materialsPassed"] = detail.get("passed_material_count")
    current_out["materialsTotal"] = detail.get("total_material_count")
    return {
        "fetchedAt": _iso(now),
        "current": current_out,
        "next": _month(following),
        "remaining": remaining,
        "tests": tests,
        "overdue": sum(1 for m in ordered if _deadline(m) < now and not _is_done(m)),
        "year": {"passed": sum(m["passed_chapter_count"] for m in summaries),
                 "total": sum(m["total_chapter_count"] for m in summaries)},
    }
