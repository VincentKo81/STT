import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.minutes import generate_minutes_docx


MINUTES_MD = """## 회의 정보
- 회의명: 테스트 회의
- 일시: 2026.06.04
- 장소: 회의실
- 참석자: 홍길동
- 주제: 테스트

## 1. 회의 개요
○ 테스트 항목 확인함
"""


class GenerateMinutesDocxTest(unittest.TestCase):
    def test_node_output_is_decoded_as_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            expected = out_dir / "테스트_회의록.docx"

            with patch("pipeline.minutes.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess(
                    args=["node"],
                    returncode=0,
                    stdout=f"OK:{expected}\n",
                    stderr="",
                )

                path = generate_minutes_docx(MINUTES_MD, {}, out_dir, today="2026.06.04")

            self.assertEqual(path, expected)
            kwargs = run.call_args.kwargs
            self.assertEqual(kwargs["encoding"], "utf-8")
            self.assertEqual(kwargs["errors"], "replace")

    def test_missing_stdout_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)

            with patch("pipeline.minutes.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess(
                    args=["node"],
                    returncode=0,
                    stdout=None,
                    stderr="",
                )

                path = generate_minutes_docx(MINUTES_MD, {}, out_dir, today="2026.06.04")

            self.assertTrue(str(path).endswith("_회의록.docx"))


if __name__ == "__main__":
    unittest.main()
