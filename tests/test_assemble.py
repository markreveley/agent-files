import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
import helpers  # noqa
from agent_files import assemble, thread as T


def req(text, system="SYS"):
    return assemble.build_request(T.parse(text), system, "m", 100)


class Assembly(unittest.TestCase):
    def test_basic_and_system(self):
        r = req("## you · t1\nhi\nEND\n")
        self.assertEqual(r["system"], "SYS")
        self.assertEqual(r["messages"], [{"role": "user", "content": "hi"}])
        self.assertNotIn("system", req("## you · t1\nhi\nEND\n", system=""))

    def test_carry_placement(self):
        r = req("---\nkind: fork\n---\n\n## carry\nquoted\n\n## you · t1\nq\nEND\n")
        self.assertEqual(r["messages"][0]["content"], "<carry>\nquoted\n</carry>\n\nq")

    def test_empty_dropped_and_merged(self):
        t = ("## you · t1\na\nEND\n## agent · t2\nEND (interrupted)\n## you · t3\nb\nEND\n"
             "## agent · t4\n\nEND\n## you · t5\nc\nEND\n")
        m = req(t)["messages"]
        self.assertEqual(m, [{"role": "user", "content": "a\n\nb\n\nc"}])

    def test_diagnostics_excluded(self):
        t = "## you · t1\na\nEND\n## agent · t2\ntext\n! error: x\nEND (failed)\n## you · t3\nb\nEND\n"
        m = req(t)["messages"]
        self.assertEqual(m[1], {"role": "assistant", "content": "text"})

    def test_leading_assistant(self):
        t = "## agent · t2\nhello\nEND\n## you · t3\nb\nEND\n"
        m = req(t)["messages"]
        self.assertEqual(m[0], {"role": "user", "content": "(conversation continues)"})
        self.assertEqual(m[1]["role"], "assistant")

    def test_notes_excluded(self):
        t = "## you · t1\na\nEND\n## note · inbox · t2\nn\nEND\n## you · t3\nb\nEND\n"
        self.assertEqual(req(t)["messages"], [{"role": "user", "content": "a\n\nb"}])

    def test_determinism(self):
        t = "## you · t1\na\nEND\n## agent · t2\nb\nEND\n## you · t3\nc\nEND\n"
        self.assertEqual(assemble.dumps(req(t)), assemble.dumps(req(t)))

    def test_agent_frontmatter(self):
        fm, body = assemble.split_frontmatter("---\nmodel: claude-x\n---\nYou are X.\n")
        self.assertEqual((fm["model"], body), ("claude-x", "You are X."))


if __name__ == "__main__":
    unittest.main()
