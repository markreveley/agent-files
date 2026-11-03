import json, os, re, subprocess, sys, unittest
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
        self.assertEqual(s["context_edit_pct"], 100.0)
        self.assertEqual(s["model_switches"], 1)
        self.assertEqual(s["searches"], 2)
        self.assertEqual(s["observed_sessions"], 2)
        self.assertEqual(s["observed_blocked_events"], 2)
        self.assertEqual(s["carry_median_lines"], 2)
        r = subprocess.run([sys.executable, STATS], env=self.e.env, capture_output=True, text=True)
        self.assertIn("H1 go", r.stdout)
        self.assertIn("(100.0%)", r.stdout)
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

    # ---- helpers for the tests below -------------------------------------------------------

    def reply(self, tid, q, edit=None):
        """Optionally edit the thread, fill its trailing empty `## you` turn with `q`, and send."""
        txt = self.e.read(tid)
        if edit:
            self.assertIn(edit[0], txt)
            txt = txt.replace(*edit)
        txt, n = re.subn(r"(## you · t\d+)\n\n$", lambda m: f"{m.group(1)}\n{q}\nEND\n", txt)
        self.assertEqual(n, 1, txt)
        self.send(tid, txt)

    def commit(self, tid, body, event="reply", date=None):
        """Write threads/<tid>/thread.md and commit only it, with runner-style trailers."""
        rel = f"threads/{tid}/thread.md"
        self.e.write_thread(tid, body)
        env = dict(self.e.env, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        msg = f"{event} {tid}\n\nAgent-Files-Event: {event}\nAgent-Files-Thread: {tid}\n"
        for cmd in (["add", "--", rel], ["commit", "-q", "-m", msg, "--only", "--", rel]):
            r = subprocess.run(["git", "-C", self.e.root, *cmd], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    # ---- fix: retrying an abnormally closed agent turn is not a context edit --------------

    def test_retrying_a_failed_turn_is_not_a_context_edit(self):
        self.e.write_thread("r", "## you · t1\nq1\nEND\n", model="mock/fail")
        self.send("r")
        txt = self.e.read("r")
        self.assertIn("END (failed)", txt)
        txt = txt[:txt.index("## agent · t2")].rstrip("\n") + "\n"     # delete the failed turn: t1 is sent again
        self.send("r", txt.replace("model: mock/fail", "model: mock/echo"))
        self.assertIn("echo: q1", self.e.read("r"))
        s = self.stats()
        self.assertEqual(s["threads_with_context_edit"], 0)
        self.assertEqual(s["model_switches"], 1)

    def test_only_removing_abnormal_agent_turns_is_exempt(self):
        Q = "## you · t1\nq1\nEND\n\n"
        FAILED = "## agent · t2\npartial\n! error: x\nEND (failed)\n\n"
        cases = [   # (thread, before, after, is a context edit)
            ("failed", Q + FAILED + "## you · t3\n\n", Q, False),
            ("interrupted", Q + "## agent · t2\npartial\nEND (interrupted)\n\n## you · t3\n\n",
             Q + "## you · t3\nagain\nEND\n", False),
            ("conflict", Q + "## agent · t2\npartial\nEND (conflict)\n", Q, False),
            ("kept", Q + FAILED + "## you · t3\n\n", Q + FAILED + "## you · t3\nmore\nEND\n", False),
            ("normal-agent-deleted", Q + "## agent · t2\nanswer\nEND\n\n## you · t3\n\n", Q, True),
            ("failed-and-premise", Q + FAILED + "## you · t3\n\n", Q.replace("q1", "q1 fixed"), True),
            ("failed-turn-edited", Q + FAILED + "## you · t3\n\n",
             Q + FAILED.replace("partial", "part") + "## you · t3\nmore\nEND\n", True),
        ]
        for tid, before, after, edit in cases:
            with self.subTest(tid):
                n = self.stats()["threads_with_context_edit"]
                self.commit(tid, before)
                self.commit(tid, after, event="send")
                self.assertEqual(self.stats()["threads_with_context_edit"] - n, int(edit))

    # ---- fix: the H1 percentage is not rounded across a threshold ---------------------------

    def test_context_edit_pct_is_cut_to_one_decimal(self):
        body = turns(3)                                               # 6 turns each
        for n, k, pct in ((21, 1, 4.7), (41, 8, 19.5), (101, 5, 4.9)):
            with self.subTest(f"{k}/{n}"):
                self.e.cleanup()
                self.e = Env().init()
                for i in range(n):
                    self.e.write_thread(f"s{i:03d}", body)
                self.e.git("add", "-A", "threads")
                self.e.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "seed")
                for i in range(k):
                    self.commit(f"s{i:03d}", body.replace("q1", "q1 edited"), event="send")
                s = self.stats()
                self.assertEqual((s["threads_6plus"], s["threads_6plus_with_context_edit"]), (n, k))
                self.assertEqual(s["context_edit_pct"], pct)
                self.assertLess(s["context_edit_pct"], 20 if pct > 5 else 5)    # below the threshold, as k/n is
                r = subprocess.run([sys.executable, STATS], env=self.e.env, capture_output=True, text=True)
                self.assertIn(f"({pct}%)", r.stdout)

    # ---- fix: --since YYYY-MM-DD starts at local midnight ----------------------------------

    def test_since_date_starts_at_local_midnight(self):
        self.e.env["TZ"] = "EST5"                                     # git and stats both use local time
        Q = "## you · t1\nq1\nEND\n"
        for tid in ("early", "late"):
            self.commit(tid, Q, date="2026-01-14T12:00:00-05:00")
        self.commit("early", Q.replace("q1", "q1 edited"), event="send", date="2026-01-14T23:55:00-05:00")
        self.commit("late", Q.replace("q1", "q1 edited"), event="send", date="2026-01-15T00:05:00-05:00")
        self.assertEqual(self.stats()["threads_with_context_edit"], 2)
        self.assertEqual(self.stats("--since", "2026-01-15")["threads_with_context_edit"], 1)   # 'late' only

    # ---- fix: renamed threads keep their edits and are not counted twice -------------------

    def test_rename_keeps_context_edits(self):
        for tid in ("x", "p"):
            self.e.write_thread(tid, "## you · t1\nq1\nEND\n")
            self.send(tid)
            self.reply(tid, "q3", edit=("q1", "q1 edited"))           # a context edit, sent as x / p
            self.reply(tid, "q5")                                     # 6 turns
        os.rename(self.e.tdir("x"), self.e.tdir("y"))
        self.reply("y", "q7")                                         # renamed, then sent again
        os.rename(self.e.tdir("p"), self.e.tdir("q"))                 # renamed, not sent since
        s = self.stats()
        self.assertEqual(s["threads"], 2)
        self.assertEqual(s["threads_6plus"], 2)
        self.assertEqual(s["threads_6plus_with_context_edit"], 2)
        self.assertEqual(s["threads_with_context_edit"], 2)

    def test_edit_made_while_renaming_counts(self):
        self.e.write_thread("m", "## you · t1\nq1\nEND\n")
        self.send("m")
        self.reply("m", "q3")
        self.reply("m", "q5")
        os.rename(self.e.tdir("m"), self.e.tdir("n"))
        self.reply("n", "q7", edit=("q1", "q1 fixed"))                # first send under the new name carries an edit
        s = self.stats()
        self.assertEqual(s["threads_6plus_with_context_edit"], 1)
        self.assertEqual(s["threads_with_context_edit"], 1)

    def test_renamed_fork_with_edited_carry_counts_once(self):
        self.e.write_thread("x", "## you · t1\nq\nEND\n")
        self.send("x")
        self.fork("x/f1")
        self.reply("x/f1", "more", edit=("carried line", "carried line, fixed"))   # carry edited and sent...
        os.rename(self.e.tdir("x/f1"), self.e.tdir("x/f2"))                          # ...then renamed
        self.reply("x/f2", "again")
        self.fork("x/g1", carry="other line\n")
        os.rename(self.e.tdir("x/g1"), self.e.tdir("x/g2"))                          # renamed with an unsent carry edit
        self.reply("x/g2", "more", edit=("other line", "other line, fixed"))
        s = self.stats()
        self.assertEqual((s["threads"], s["forks"]), (3, 2))
        self.assertEqual(s["threads_with_context_edit"], 2)


if __name__ == "__main__":
    unittest.main()
