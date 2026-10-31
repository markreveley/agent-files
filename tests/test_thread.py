import os, sys, random, tempfile, unittest, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from agent_files import thread as T

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
ROOT = os.path.join(os.path.dirname(__file__), "..")

BASIC = """---
agent: default
runtime: direct
model: null
tags: [a, b]
---

## you · t1
hello
END

## agent · t2
hi there
END

## you · t3

"""


class Parser(unittest.TestCase):
    def test_basic(self):
        th = T.parse(BASIC)
        self.assertEqual(th.frontmatter["agent"], "default")
        self.assertIsNone(th.frontmatter["model"])
        self.assertEqual(th.frontmatter["tags"], ["a", "b"])
        self.assertEqual([(t.role, t.id, t.closed) for t in th.turns],
                         [("you", 1, "ok"), ("agent", 2, "ok"), ("you", 3, "none")])
        self.assertEqual(th.turns[0].body, "hello")

    def test_end_variants(self):
        for kind in ("interrupted", "failed", "conflict"):
            th = T.parse(f"## agent · t2\nx\nEND ({kind})\n")
            self.assertEqual(th.turns[0].closed, kind)

    def test_markers_inside_fences(self):
        th = T.parse("## you · t1\n```\nEND\n## you · t9\n```\nreal\nEND\n")
        self.assertEqual(len(th.turns), 1)
        self.assertEqual(th.turns[0].closed, "ok")
        self.assertIn("## you · t9", th.turns[0].body)

    def test_tilde_fence_indented(self):
        th = T.parse("## you · t1\n   ~~~\nEND\n   ~~~\nEND\n")
        self.assertEqual(len(th.turns), 1)

    def test_dot_alternatives(self):
        for h in ("## you - t4", "## you . t4", "## you · t4"):
            self.assertEqual(T.parse(h + "\nx\nEND\n").turns[0].id, 4)

    def test_implicit_close_human(self):
        th = T.parse("## you · t1\na\n## you · t3\nb\nEND\n")
        self.assertEqual(th.turns[0].closed, "ok")
        self.assertIsNone(th.malformed)

    def test_malformed_agent(self):
        th = T.parse("## agent · t2\npartial\n## you · t3\nx\nEND\n")
        self.assertTrue(th.malformed)
        self.assertFalse(T.is_send(th, None))

    def test_text_before_first_header(self):
        th = T.parse("---\na: b\n---\nstray\n## you · t1\nx\nEND\n")
        self.assertTrue(th.warnings)
        self.assertEqual(len(th.turns), 1)

    def test_carry(self):
        th = T.parse("---\nkind: fork\n---\n\n## carry\nquoted\nlines\n\n## you · t1\nq\nEND\n")
        self.assertEqual(th.carry, "quoted\nlines")
        self.assertEqual(len(th.turns), 1)

    def test_carry_unescapes_markers(self):
        th = T.parse("## carry\n\\END\n\\## you · t9\n\n## you · t1\nq\nEND\n")
        self.assertEqual(th.carry, "END\n## you · t9")

    def test_carry_not_first_is_text(self):
        th = T.parse("## you · t1\nx\nEND\n## carry\nfoo\n")
        self.assertIsNone(th.carry)

    def test_note_header(self):
        th = T.parse("## note · inbox · t5\nhey\nEND\n")
        self.assertEqual((th.turns[0].role, th.turns[0].source, th.turns[0].id), ("note", "inbox", 5))

    def test_diagnostics(self):
        th = T.parse("## agent · t2\ntext\n! error: boom\nEND (failed)\n")
        self.assertEqual(th.turns[0].body, "text")
        self.assertEqual(th.turns[0].diagnostics, ["error: boom"])
        # a '! ' line in a human turn is plain text
        th = T.parse("## you · t1\n! not diag\nEND\n")
        self.assertEqual(th.turns[0].body, "! not diag")

    def test_escaped_markers_in_body(self):
        th = T.parse("## agent · t2\n\\END\n\\## you · t9\n\\! x\nEND\n")
        self.assertEqual(th.turns[0].body, "END\n## you · t9\n! x")
        self.assertEqual(len(th.turns), 1)

    def test_frontmatter_values(self):
        th = T.parse("---\nproject: /Users/m/code/api\nstarted: 2026-11-02T10:14:03Z\ngrounding: []\nmodel: 'x'\n---\n")
        self.assertEqual(th.frontmatter["started"], "2026-11-02T10:14:03Z")
        self.assertEqual(th.frontmatter["grounding"], [])
        self.assertEqual(th.frontmatter["model"], "x")

    def test_round_trip_fixtures(self):
        files = glob.glob(os.path.join(FIX, "*.md")) + glob.glob(os.path.join(ROOT, "docs", "examples", "**", "thread.md"), recursive=True)
        self.assertTrue(files)
        for f in files:
            txt = open(f, encoding="utf-8").read()
            self.assertEqual(T.parse(txt).serialize(), txt, f)

    def test_round_trip_odd(self):
        for txt in ["", "\n", BASIC, BASIC + "stray", "---\na: b\n---\n", "junk\n## you · t1\nx\nEND\n\n\nmore junk\n\n## agent · t2\ny\nEND (failed)\n"]:
            self.assertEqual(T.parse(txt).serialize(), txt)


class Escaping(unittest.TestCase):
    def test_property(self):
        rnd = random.Random(7)
        atoms = ["END", "## you · t1", "## agent", "## carry", "## note", "! x", "\\", "\\\\", "text", " ", "ENDING", "!", "#"]
        for _ in range(3000):
            line = "".join(rnd.choice(atoms) + rnd.choice(["", " ", "\\"]) for _ in range(rnd.randint(0, 4)))
            self.assertEqual(T.unescape_line(T.escape_line(line)), line, repr(line))

    def test_escaped_never_marker(self):
        for line in ["END", "## you · t99", "! x", "\\END", "## agent · t3", "END (failed)"]:
            e = T.escape_line(line)
            th = T.parse("## agent · t2\n" + e + "\nEND\n")
            self.assertEqual(len(th.turns), 1)
            self.assertEqual(th.turns[0].body, line)


class Ids(unittest.TestCase):
    def test_next_id_sidecar_and_gaps(self):
        th = T.parse("## you · t1\nx\nEND\n## agent · t2\ny\nEND\n")
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(T.next_id(th, d), 3)
            open(os.path.join(d, "last_turn"), "w").write("t7\n")
            self.assertEqual(T.next_id(th, d), 8)
        th = T.parse("## you · t1\nx\nEND\n## agent · t5\ny\nEND\n")
        self.assertEqual(T.next_id(th, None), 6)


class Send(unittest.TestCase):
    def test_cases(self):
        self.assertFalse(T.is_send(T.parse("## you · t1\nhello\n"), None))            # draft
        self.assertTrue(T.is_send(T.parse("## you · t1\nhello\nEND\n"), None))
        self.assertTrue(T.is_send(T.parse("## you · t1\nhello\nEND\n"), "done"))
        self.assertFalse(T.is_send(T.parse("## you · t1\nhello\nEND\n"), "working"))
        self.assertFalse(T.is_send(T.parse("## you · t1\n\nEND\n"), None))             # empty
        self.assertFalse(T.is_send(T.parse("## you · t1\n```\nhello\nEND\n"), None))   # END in fence
        self.assertFalse(T.is_send(T.parse("## you · t1\nq\nEND\n## agent · t2\na\nEND\n"), None))
        self.assertFalse(T.is_send(T.parse("## you · t1\nq\nEND\n## agent · t2\na\nEND\n## you · t3\n\n"), None))
        self.assertFalse(T.is_send(T.parse(""), None))


if __name__ == "__main__":
    unittest.main()
