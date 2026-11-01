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

    def stats(self, *args):
        r = subprocess.run([sys.executable, STATS, "--json", *args], env=self.e.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def fork(self, tid, carry="carried line\n"):
        self.e.write_thread(tid, f"## carry\n{carry}\n## you · t1\nq\nEND\n")
        sub(os.path.join(self.e.tdir(tid), "thread.md"), "kind: main", "kind: fork")
        self.send(tid)

    def test_renamed_threads_count_once(self):
        self.e.write_thread("x", "## you · t1\nq\nEND\n")
        self.send("x")
        self.fork("x/f1")
        os.rename(self.e.tdir("x/f1"), self.e.tdir("x/f2"))          # rename a fork
        txt = self.e.read("x/f2").replace("## you · t3\n\n", "## you · t3\nmore\nEND\n")
        self.send("x/f2", txt)
        os.rename(self.e.tdir("x"), self.e.tdir("y"))                # rename its parent (a main thread)
        txt = self.e.read("y").replace("## you · t3\n\n", "## you · t3\nmore\nEND\n")
        self.send("y", txt)
        s = self.stats()
        self.assertEqual(s["threads"], 2)                             # y, y/f2
        self.assertEqual(s["forks"], 1)

    def test_fork_created_and_deleted_same_day(self):
        self.e.write_thread("x", "## you · t1\nq\nEND\n")
        self.send("x")
        self.fork("x/sent")                                           # sent once, then deleted: a fork you made
        subprocess.run(["rm", "-rf", self.e.tdir("x/sent")])
        os.makedirs(self.e.tdir("x/never"))                           # created, never sent, deleted: not in history
        self.e.write_thread("x/never", "## carry\nc\n\n## you · t1\ndraft\n")
        subprocess.run(["rm", "-rf", self.e.tdir("x/never")])
        s = self.stats()
        self.assertEqual(s["threads"], 1)
        self.assertEqual(s["forks"], 1)

    def test_since_filters_sends_not_threads(self):
        self.e.write_thread("a", "## you · t1\nq1\nEND\n")
        self.send("a")
        txt = self.e.read("a").replace("q1", "q1 edited").replace("## you · t3\n\n", "## you · t3\nq3\nEND\n")
        self.send("a", txt)                                           # a context edit, today
        self.fork("a/f")
        s = self.stats("--since", "2999-01-01")
        self.assertEqual(s["model_switches"], 0)
        self.assertEqual(s["threads_6plus_with_context_edit"], 0)     # sends are filtered...
        self.assertEqual((s["threads"], s["forks"]), (2, 1))          # ...thread and fork counts are not (spec §7.3)


if __name__ == "__main__":
    unittest.main()
