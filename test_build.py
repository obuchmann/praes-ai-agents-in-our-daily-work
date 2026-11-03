"""Tests for build.py. Run: python3 -m unittest"""
import pathlib
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build  # noqa: E402

HEAD = "speakers: oliver=blue, andi=yellow\n\n"


def run(md):
    with tempfile.TemporaryDirectory() as d:
        src, dst = pathlib.Path(d, "talk.md"), pathlib.Path(d, "talk.html")
        src.write_text(md, encoding="utf-8")
        build.build(src, dst)
        return dst.read_text(encoding="utf-8")


class TalkTest(unittest.TestCase):
    def test_talk_md_builds(self):
        out = run(build.HERE.joinpath("talk.md").read_text(encoding="utf-8"))
        self.assertEqual(out.count('<section class="slide'), 11)
        self.assertEqual(out.count("Then live demo:"), 4)
        self.assertNotIn("{{", out)
        self.assertIsNone(re.search(r'<(script|link|img)[^>]+(src|href)="https?://', out))

    def test_name_on_slide_fails(self):
        with self.assertRaisesRegex(build.TalkError, "shows the name 'andi'"):
            run(HEAD + "# Hello Andi\nspeaker: andi\n")

    def test_name_in_notes_is_fine(self):
        out = run(HEAD + "# Hello\nspeaker: andi\n\nNote: Andi starts.\n")
        self.assertIn("Andi starts.", out)

    def test_link_on_slide_fails(self):
        with self.assertRaisesRegex(build.TalkError, "shows a link"):
            run(HEAD + "# Hello\nspeaker: andi\n\n- see https://example.org\n")

    def test_unknown_speaker_fails(self):
        with self.assertRaisesRegex(build.TalkError, "unknown speaker 'bob'"):
            run(HEAD + "# Hello\nspeaker: bob\n")

    def test_demo_after_adds_dashed_show_cell(self):
        out = run(HEAD + "# A\nspeaker: oliver\ndemo-after: Demo (andi) #d\n\n# B\nspeaker: andi\n")
        self.assertIn('class="yellow live', out)
        self.assertIn("After the demo: press → for B.", out)

    def test_two_speakers_show_both_cell_in_track(self):
        out = run(HEAD + "# T\nkind: title\nspeaker: oliver, andi\n")
        self.assertIn('<i class="both', out)
        self.assertNotIn('class="band"', out)


if __name__ == "__main__":
    unittest.main()
