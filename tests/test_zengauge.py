import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zengauge import api, paths, session, summary, sync  # noqa: E402

WIDGET = ROOT / "scriptable" / "ZEN Study進捗.js"

# Synthetic data in the API's shape (no real account data).
OVERVIEW = {
    "service": "basic",
    "monthly_summaries": [
        {"year": 2030, "month": 4, "earliest_report_deadline": "2030-04-15T23:59:59+09:00",
         "total_chapter_count": 5, "passed_chapter_count": 5, "total_assessment_test": 0, "passed_assessment_test_count": 0},
        {"year": 2030, "month": 5, "earliest_report_deadline": "2030-05-15T23:59:59+09:00",
         "total_chapter_count": 6, "passed_chapter_count": 2, "total_assessment_test": 1, "passed_assessment_test_count": 0},
        {"year": 2030, "month": 6, "earliest_report_deadline": "2030-06-15T23:59:59+09:00",
         "total_chapter_count": 7, "passed_chapter_count": 0, "total_assessment_test": 2, "passed_assessment_test_count": 0},
        {"year": 2030, "month": 3, "earliest_report_deadline": "2030-03-15T23:59:59+09:00",
         "total_chapter_count": 4, "passed_chapter_count": 3, "total_assessment_test": 0, "passed_assessment_test_count": 0},
    ],
}
DETAIL = {
    "passed_material_count": 40, "total_material_count": 60,
    "passed_assessment_tests": [{"assessment_test_id": 9}],
    "deadline_groups": [{
        "deadline": "2030-05-15T23:59:59+09:00",
        "chapters": [
            {"subject_category_title": "数学", "chapter_title": "第1回", "passed_count": 3, "total_count": 10, "exempted": False},
            {"subject_category_title": "英語", "chapter_title": "第2回", "passed_count": 9, "total_count": 10, "exempted": False},
            {"subject_category_title": "体育", "chapter_title": "第3回", "passed_count": 0, "total_count": 5, "exempted": True},
            {"subject_category_title": "国語", "chapter_title": "第4回", "passed_count": 8, "total_count": 8, "exempted": False},
        ],
        "assessment_tests": [
            {"assessment_test_id": 8, "subject_category_title": "数学", "title": "定期テスト", "total_question": 30, "total_answered_question": 4},
            {"assessment_test_id": 9, "subject_category_title": "英語", "title": "定期テスト", "total_question": 20, "total_answered_question": 20},
        ],
    }],
}
NOW = datetime(2030, 5, 10, 3, 0, tzinfo=timezone.utc)


class SummaryTests(unittest.TestCase):
    def test_picks_first_open_unfinished_month(self):
        self.assertEqual(summary.pick_month(OVERVIEW["monthly_summaries"], NOW)["month"], 5)

    def test_summary_shape(self):
        data = summary.summarize(OVERVIEW, DETAIL, NOW)
        self.assertEqual(data["current"]["month"], 5)
        self.assertEqual(data["current"]["deadline"], "2030-05-15T14:59:59Z")
        self.assertEqual((data["current"]["materialsPassed"], data["current"]["materialsTotal"]), (40, 60))
        self.assertEqual(data["next"]["month"], 6)
        self.assertEqual([c["subject"] for c in data["remaining"]], ["英語", "数学"])
        self.assertEqual([t["subject"] for t in data["tests"]], ["数学"])
        self.assertEqual(data["overdue"], 1)  # March is past and unfinished
        self.assertEqual(data["year"], {"passed": 10, "total": 22})

    def test_after_all_deadlines_shows_last_month(self):
        later = datetime(2031, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(summary.summarize(OVERVIEW, None, later)["current"]["month"], 6)

    def test_matches_widget_javascript(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node unavailable")
        source = WIDGET.read_text(encoding="utf-8")
        start, end = source.index("const deadlineOf"), source.index("async function fetchProgress")
        script = source[start:end] + (
            "\nconst [o, d, now] = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
            "\nprocess.stdout.write(JSON.stringify(summarize(o, d, new Date(now))));")
        result = subprocess.run([node, "-e", script], input=json.dumps([OVERVIEW, DETAIL, NOW.isoformat()]),
                                capture_output=True, text=True, check=True)
        widget = json.loads(result.stdout)
        python = summary.summarize(OVERVIEW, DETAIL, NOW)
        # JavaScript prints milliseconds in ISO strings; compare the instants.
        for data in (widget, python):
            data["fetchedAt"] = data["fetchedAt"][:19]
            for month in (data["current"], data["next"]):
                month["deadline"] = month["deadline"][:19]
        self.assertEqual(widget, python)


class SessionAndSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        patcher = mock.patch.dict(os.environ, {"ZENGAUGE_HOME": str(self.home / "data")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.out = self.home / "scriptable"
        self.out.mkdir()

    def test_import_cookie_header_requires_session_cookie(self):
        with self.assertRaises(session.LoginRequired):
            session.import_cookie_header("authority=1")
        path = session.import_cookie_header("_zane_session=abc; authority=1")
        self.assertEqual(session.cookie_header(session.load_cookies(path)), "_zane_session=abc; authority=1")
        if os.name != "nt":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_import_storage_state_drops_other_sites(self):
        source = self.home / "state.json"
        source.write_text(json.dumps({"cookies": [
            {"name": "_zane_session", "value": "a", "domain": ".nnn.ed.nico"},
            {"name": "other", "value": "b", "domain": ".example.com"},
        ]}))
        session.import_storage_state(source)
        self.assertEqual([c["name"] for c in session.load_cookies()], ["_zane_session"])

    def test_sync_writes_progress_and_keeps_it_when_login_expires(self):
        session.import_cookie_header("_zane_session=abc")
        with mock.patch.object(api, "overview", return_value=OVERVIEW), \
             mock.patch.object(api, "monthly", return_value=DETAIL) as monthly:
            status, path = sync.run(self.out)
        self.assertEqual(status, "ok")
        monthly.assert_called_once()
        written = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(written["status"], "ok")
        self.assertIn("current", written)

        with mock.patch.object(api, "overview", side_effect=api.AuthExpired("ログインが切れています")), \
             mock.patch.object(sync, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime.now(timezone.utc).replace(year=2099)
            status, path2 = sync.run(self.out)
        self.assertEqual(status, "login_required")
        self.assertNotEqual(path, path2)
        self.assertEqual(sync.progress_files(self.out), [path2])  # older file cleaned up
        written = sync.latest(self.out)
        self.assertEqual(written["status"], "login_required")
        self.assertEqual(written["current"]["month"], summary.summarize(OVERVIEW, DETAIL, datetime.now(timezone.utc))["current"]["month"])

    def test_sync_without_login(self):
        status, path = sync.run(self.out)
        self.assertEqual(status, "login_required")
        self.assertEqual(sync.latest(self.out)["status"], "login_required")
        self.assertTrue(path.name.startswith(paths.PROGRESS_PREFIX))

    def test_configured_scriptable_dir(self):
        self.assertEqual(paths.find_scriptable_dir(str(self.out)), self.out)
        self.assertIsNone(paths.find_scriptable_dir(str(self.home / "missing")))


if __name__ == "__main__":
    unittest.main()
