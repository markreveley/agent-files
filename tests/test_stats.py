import json, os, subprocess, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
from helpers import Env, REPO

STATS = os.path.join(REPO, "bin", "agent-files-stats")
GREP = os.path.join(REPO, "bin", "agent-files-grep")


def sub(p, a, b):
    t = open(p).read()
    with open(p, "w") as f:
        f.write(t.replace(a, b))


def turns(n):
    out = ""
    for i in range(1, n * 2, 2):
        out += f"## you · t{i}\nq{i}\nEND\n\n## agent · t{i+1}\na\nEND\n\n"
    return out


class Stats(unittest.TestCase):
    def setUp(self):
        self.e = Env().init()

    def tearDown(self):
        self.e.cleanup()

    def send(self, tid, text=None):
        """Append END to a trailing draft (or replace file with text) and run once."""
        p = os.path.join(self.e.tdir(tid), "thread.md")
        if text is not None:
            open(p, "w").write(text)
        r = self.e.run("once", tid)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_numbers(self):
        # thread a: 3 exchanges, edit above END on the second send, model switch on third
        self.e.write_thread("a", "## you · t1\nq1\nEND\n")
        self.send("a")
        txt = self.e.read("a").replace("q1", "q1 edited").replace("## you · t3\n\n", "## you · t3\nq3\nEND\n")
        self.send("a", txt)                                                  # context edit
        txt = self.e.read("a").replace("model: mock/echo", "model: mock/markers").replace("## you · t5\n\n", "## you · t5\nq5\nEND\n")
        self.send("a", txt)                                                  # model switch only
        txt = self.e.read("a").replace("## you · t7\n\n", "## you · t7\nq7\nEND\n")
        self.send("a", txt)                                                  # plain append
        txt = self.e.read("a").replace("## you · t9\n\n", "## you · t9\nq9\nEND\n")
        self.send("a", txt)
        txt = self.e.read("a").replace("## you · t11\n\n", "## you · t11\nq11\nEND\n")
        self.send("a", txt)
        # thread b: no edits, short
        self.e.write_thread("b", "## you · t1\nq\nEND\n")
        self.send("b")
        # a fork with carry
        self.e.write_thread("a/fork1", "## carry\nline one\nline two\n\n## you · t1\nq\nEND\n", extra="")
        p = os.path.join(self.e.tdir("a/fork1"), "thread.md")
        sub(p, "kind: main", "kind: fork")
        self.send("a/fork1")
        # a deleted fork
        self.e.write_thread("gone", "## you · t1\nq\nEND\n")
        p = os.path.join(self.e.tdir("gone"), "thread.md")
        sub(p, "kind: main", "kind: fork")
        self.send("gone")
        subprocess.run(["rm", "-rf", self.e.tdir("gone")])
        # searches
        r = subprocess.run(["sh", GREP, "q11"], env=self.e.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("threads/a/thread.md", r.stdout)
        subprocess.run(["sh", GREP, "zzzznomatch"], env=self.e.env, capture_output=True, text=True)
        # observed log
        os.makedirs(os.path.join(self.e.root, "trial"), exist_ok=True)
        open(os.path.join(self.e.root, "trial", "observed.log"), "w").write(
            "t\t_observed/p-1\tdone\nt\t_observed/p-1\tblocked\nt\t_observed/p-2\tblocked\n")

        r = subprocess.run([sys.executable, STATS, "--json"], env=self.e.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        s = json.loads(r.stdout)
        self.assertEqual(s["threads"], 3)                         # a, b, a/fork1 present now
        self.assertEqual(s["forks"], 2)                           # a/fork1 + deleted 'gone'
        self.assertEqual(s["threads_6plus"], 1)
        self.assertEqual(s["threads_6plus_with_context_edit"], 1)
        self.assertEqual(s["context_edit_pct"], 100)
        self.assertEqual(s["model_switches"], 1)
        self.assertEqual(s["searches"], 2)
        self.assertEqual(s["observed_sessions"], 2)
        self.assertEqual(s["observed_blocked_events"], 2)
        self.assertEqual(s["carry_median_lines"], 2)
        r = subprocess.run([sys.executable, STATS], env=self.e.env, capture_output=True, text=True)
        self.assertIn("H1 go", r.stdout)
        self.assertIn("(forks 2)", r.stdout)


if __name__ == "__main__":
    unittest.main()
