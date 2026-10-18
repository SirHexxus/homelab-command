"""Tests for lib/wiki_pages.py and the matching bash find_wiki_files().

Run from the scripts/ directory:
    python3 -m unittest discover -s tests
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS / "lib"))
from wiki_pages import bucket_pages  # noqa: E402


def make_wiki(root: Path) -> None:
    for rel in (
        "reference/Top.md",
        "reference/problems/Problem - Nested.md",
        "reference/problems/deeper/Too Deep.md",
        "ideas/Idea.md",
        "ideas/drafts/Not A Page.md",
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nbucket: X\n---\n")


class BucketPagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        make_wiki(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def stems(self, bucket: str) -> list[str]:
        return [p.stem for p in bucket_pages(self.root / bucket)]

    def test_reference_includes_one_subfolder_level(self) -> None:
        self.assertEqual(self.stems("reference"), ["Top", "Problem - Nested"])

    def test_other_buckets_stay_flat(self) -> None:
        self.assertEqual(self.stems("ideas"), ["Idea"])

    def test_missing_bucket_is_empty(self) -> None:
        self.assertEqual(self.stems("people"), [])

    def test_bash_walker_matches(self) -> None:
        # wiki-common.sh derives WIKI_DIR from its own location, so run a copy
        # of lib/ placed where it resolves to the temp wiki.
        lib_copy = self.root / "scripts" / "lib"
        lib_copy.mkdir(parents=True)
        common = (SCRIPTS / "lib" / "wiki-common.sh").read_text()
        (lib_copy / "wiki-common.sh").write_text(common)
        (self.root / "wiki").symlink_to(self.root, target_is_directory=True)
        out = subprocess.run(
            ["bash", "-c", f'source "{lib_copy}/wiki-common.sh"; find_wiki_files'],
            capture_output=True, check=True,
        ).stdout.decode()
        stems = sorted(Path(p).stem for p in out.split("\0") if p)
        self.assertEqual(stems, ["Idea", "Problem - Nested", "Top"])


if __name__ == "__main__":
    unittest.main()
