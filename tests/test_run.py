import json, os, signal, subprocess, sys, time, unittest
sys.path.insert(0, os.path.dirname(__file__))
from helpers import Env, wait_for, RUN
from agent_files import thread as T

Q = "## you · t1\nhello there\nEND\n"


class RunnerBase(unittest.TestCase):
    def setUp(self):
        self.e = Env().init()
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                p.kill()
                p.wait()
        self.e.cleanup()


class Once(RunnerBase):
    def test_init_idempotent_and_files(self):
        for f in ("config.toml", ".gitignore", "agents/default.md", "trial/journal.md", "trial/searches.log"):
            self.assertTrue(os.path.exists(os.path.join(self.e.root, f)), f)
        self.assertIn("init", self.e.git("log", "--format=%s"))
        r = self.e.run("init")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.e.git("rev-list", "--count", "HEAD").strip(), "1")

    def test_refuses_code_checkout_as_root(self):
        env = dict(self.e.env, AGENT_FILES_ROOT=os.path.dirname(os.path.dirname(RUN)))
        r = self.e.run("init", env=env)
        self.assertNotEqual(r.returncode, 0)

    def test_full_turn(self):
        self.e.write_thread("t", Q)
        r = self.e.run("once", "t")
        self.assertEqual(r.returncode, 0, r.stderr)
        text = self.e.read("t")
        th = T.parse(text)
        self.assertEqual([(t.role, t.id, t.closed) for t in th.turns], [("you", 1, "ok"), ("agent", 2, "ok"), ("you", 3, "none")])
        self.assertEqual(th.turns[1].body, "echo: hello there")
        self.assertTrue(text.endswith("## you · t3\n\n"))
        self.assertEqual(self.e.status("t"), "done")
        self.assertEqual(self.e.read("t", "last_turn").strip(), "t3")
        steps = sorted(os.listdir(os.path.join(self.e.tdir("t"), "steps")))
        self.assertEqual(steps, ["t0002.request.json", "t0002.response.json"])
        resp = json.loads(self.e.read("t", "steps/t0002.response.json"))
        self.assertEqual(resp["backend"], "mock")
        log = self.e.git("log", "--format=%s%n%(trailers:key=Agent-Files-Event,valueonly)%(trailers:key=Agent-Files-Turn,valueonly)%(trailers:key=Agent-Files-Model,valueonly)")
        self.assertIn("send t t1", log)
        self.assertIn("reply t t2", log)
        self.assertIn("mock/echo", log)

    def test_nothing_to_send_exit3(self):
        self.e.write_thread("t", "## you · t1\ndraft\n")
        self.assertEqual(self.e.run("once", "t").returncode, 3)

    def test_gitignore_keeps_sidecars_out(self):
        self.e.write_thread("t", Q)
        self.e.run("once", "t")
        tracked = self.e.git("ls-files")
        self.assertIn("threads/t/thread.md", tracked)
        self.assertIn("threads/t/steps/t0002.request.json", tracked)
        for side in ("status", "last_turn"):
            self.assertNotIn(f"threads/t/{side}", tracked)

    def test_markers_cannot_end_turn(self):
        self.e.write_thread("t", Q, model="mock/markers")
        self.e.run("once", "t")
        th = T.parse(self.e.read("t"))
        self.assertIsNone(th.malformed)
        self.assertEqual([(t.role, t.id) for t in th.turns], [("you", 1), ("agent", 2), ("you", 3)])
        body = th.turns[1].body
        for frag in ("END", "## you · t99", "! x", "\\END", "## agent · t98", "END (failed)"):
            self.assertIn(frag, body.split("\n"))
        self.assertEqual(th.turns[1].closed, "ok")   # open fence was balanced
        self.assertFalse(th.turns[1].fence_open)

    def test_fail(self):
        self.e.write_thread("t", Q, model="mock/fail")
        self.e.run("once", "t")
        text = self.e.read("t")
        th = T.parse(text)
        self.assertEqual(th.turns[1].closed, "failed")
        self.assertIn("! error: mock failure", text)
        self.assertEqual(th.turns[1].body, "first line\nsecond line")
        self.assertEqual(self.e.status("t"), "failed")
        self.assertTrue(os.path.exists(os.path.join(self.e.tdir("t"), "steps", "t0002.error.json")))
        self.assertEqual(th.turns[2].role, "you")

    def test_unknown_model_still_gets_agent_turn(self):
        self.e.write_thread("t", Q, model="nonsense")
        self.e.run("once", "t")
        th = T.parse(self.e.read("t"))
        self.assertEqual(th.turns[1].closed, "failed")
        self.assertIn("unknown model nonsense", self.e.read("t"))

    def test_resume_rejected(self):
        d = self.e.write_thread("t", Q)
        txt = open(d).read().replace("context: replay", "context: resume")
        open(d, "w").write(txt)
        self.e.run("once", "t")
        self.assertIn("! error: context: resume", self.e.read("t"))

    def test_spend_cap(self):
        self.e.write_thread("a", Q)
        self.e.run("once", "a")
        # fake spend of $9 today
        p = os.path.join(self.e.tdir("a"), "steps", "t0002.response.json")
        d = json.load(open(p)); d["cost_usd"] = 9.0; json.dump(d, open(p, "w"))
        self.e.write_thread("b", Q)
        self.e.run("once", "b")
        self.assertIn("daily spend cap reached", self.e.read("b"))
        self.assertEqual(self.e.status("b"), "failed")

    def test_edit_above_end_changes_request(self):
        self.e.write_thread("t", Q)
        self.e.run("once", "t")
        txt = self.e.read("t").replace("hello there", "EDITED ABOVE").replace("## you · t3\n\n", "## you · t3\nmore\nEND\n")
        open(os.path.join(self.e.tdir("t"), "thread.md"), "w").write(txt)
        self.e.run("once", "t")
        req = json.loads(self.e.read("t", "steps/t0004.request.json"))
        self.assertIn("EDITED ABOVE", json.dumps(req))
        self.assertEqual(req["request"]["messages"][-1]["content"], "more")

    def test_check_does_not_call_model(self):
        self.e.write_thread("t", Q, model="mock/fail")
        r = self.e.run("check", "t")
        self.assertEqual(r.returncode, 0)
        self.assertIn('"hello there"', r.stdout)
        self.assertEqual(self.e.status("t"), None)

    def test_lock_second_runner_exits_2(self):
        p = self.e.popen("watch")
        self.procs.append(p)
        self.assertTrue(wait_for(lambda: os.path.exists(os.path.join(self.e.state, "agent-files", "run.lock"))))
        time.sleep(0.5)
        r = self.e.run("once", "whatever")      # nonexistent thread -> exit 1 before lock; use a real one
        self.e.write_thread("t", Q)
        r = self.e.run("once", "t")
        self.assertEqual(r.returncode, 2)
        r = self.e.run("watch")
        self.assertEqual(r.returncode, 2)


class Watch(RunnerBase):
    def start(self):
        p = self.e.popen("watch")
        self.procs.append(p)
        time.sleep(0.6)
        return p

    def test_watch_picks_up_send(self):
        self.start()
        self.e.write_thread("t", "## you · t1\nhi\n")           # draft: nothing
        time.sleep(0.8)
        self.assertIsNone(self.e.status("t"))
        with open(os.path.join(self.e.tdir("t"), "thread.md"), "a") as f:
            f.write("END\n")
        self.assertTrue(wait_for(lambda: self.e.status("t") == "done"))
        self.assertIn("echo: hi", self.e.read("t"))

    def test_pending_send_at_startup(self):
        self.e.write_thread("t", Q)
        self.start()
        self.assertTrue(wait_for(lambda: self.e.status("t") == "done"))

    def test_stop(self):
        self.e.write_thread("t", Q, model="mock/slow")
        self.start()
        self.assertTrue(wait_for(lambda: "line 3" in self.e.read("t")))
        self.assertEqual(self.e.status("t"), "working")
        open(os.path.join(self.e.tdir("t"), "STOP"), "w").close()
        self.assertTrue(wait_for(lambda: self.e.status("t") == "interrupted"))
        th = T.parse(self.e.read("t"))
        self.assertEqual(th.turns[1].closed, "interrupted")
        self.assertEqual(th.turns[2].role, "you")
        self.assertFalse(os.path.exists(os.path.join(self.e.tdir("t"), "STOP")))

    def test_conflict(self):
        self.e.write_thread("t", Q, model="mock/slow")
        self.start()
        self.assertTrue(wait_for(lambda: "line 3" in self.e.read("t")))
        with open(os.path.join(self.e.tdir("t"), "thread.md"), "a") as f:
            f.write("foreign write\n")
        self.assertTrue(wait_for(lambda: self.e.status("t") == "interrupted"))
        text = self.e.read("t")
        self.assertTrue(text.rstrip().endswith("END (conflict)"))
        self.assertEqual(text.count("## you · t3"), 0)
        out = os.path.join(self.e.tdir("t"), "out", "t0002-conflict.txt")
        self.assertTrue(os.path.exists(out))
        self.assertIn("line 1", open(out).read())

    def test_crash_then_recover(self):
        self.e.write_thread("t", Q, model="mock/slow")
        p = self.start()
        self.assertTrue(wait_for(lambda: "line 3" in self.e.read("t")))
        p.send_signal(signal.SIGKILL); p.wait()
        self.assertEqual(self.e.status("t"), "working")
        r = self.e.run("once", "nothing-here") if False else None
        p2 = self.start()
        self.assertTrue(wait_for(lambda: self.e.status("t") == "interrupted"))
        th = T.parse(self.e.read("t"))
        self.assertEqual([(t.role, t.closed) for t in th.turns], [("you", "ok"), ("agent", "interrupted"), ("you", "none")])
        time.sleep(1.0)
        self.assertEqual(len([t for t in T.parse(self.e.read("t")).turns if t.role == "agent"]), 1)   # no duplicate
        self.assertIn("recover t", self.e.git("log", "--format=%s"))


if __name__ == "__main__":
    unittest.main()
