import json, os, subprocess, sys, time, unittest
sys.path.insert(0, os.path.dirname(__file__))
from helpers import Env, REPO

STATS = os.path.join(REPO, "bin", "agent-files-stats")
GREP = os.path.join(REPO, "bin", "agent-files-grep")


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

    def stats(self, *args):
        r = subprocess.run([sys.executable, STATS, "--json", *args], env=self.e.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def response(self, tid, n, cost, day=None):
        """Write threads/<tid>/steps/t<n>.response.json with `cost`, dated local noon on `day`."""
        d = os.path.join(self.e.tdir(tid), "steps")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"t{n:04d}.response.json")
        with open(p, "w") as f:
            json.dump({"cost_usd": cost}, f)
        if day:
            t = time.mktime(time.strptime(day + " 12", "%Y-%m-%d %H"))
            os.utime(p, (t, t))

    def observed(self, name, status):
        d = os.path.join(self.e.root, "threads", "_observed", name)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "thread.md"), "w").write("---\nruntime: observed\n---\n")
        open(os.path.join(d, "status"), "w").write(status + "\n")

    def test_numbers(self):
        self.e.write_thread("a", turns(3))
        self.e.write_thread("b", turns(1))
        self.e.write_thread("a/fork1", "## carry\nc\n\n" + turns(2))
        today = time.strftime("%Y-%m-%d")
        self.response("a", 2, 0.25, "2026-01-14")
        self.response("a", 4, 0.5)
        self.response("b", 2, 0.125, "2026-01-15")
        self.response("a/fork1", 2, 1.0)
        self.observed("p-1", "blocked")
        self.observed("p-2", "blocked")
        self.observed("q-1", "working")
        s = self.stats()
        self.assertEqual(s["threads"], 3)                          # observed sessions are not threads
        self.assertEqual((s["turns_median"], s["turns_max"]), (4, 6))
        self.assertEqual(s["spend_usd"], 1.875)
        self.assertEqual(s["spend_today_usd"], 1.5)
        self.assertEqual(s["spend_by_day_usd"], {"2026-01-14": 0.25, "2026-01-15": 0.125, today: 1.5})
        self.assertEqual(list(s["spend_by_thread_usd"].items()), [("a/fork1", 1.0), ("a", 0.75), ("b", 0.125)])
        self.assertEqual(s["observed_sessions"], 3)
        self.assertEqual(s["observed_by_status"], {"blocked": 2, "working": 1})
        r = subprocess.run([sys.executable, STATS], env=self.e.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("$1.88 (today $1.50)", r.stdout)
        self.assertIn("(blocked 2, working 1)", r.stdout)

    def test_since_filters_spend_not_threads(self):
        self.e.write_thread("a", turns(1))
        self.response("a", 2, 0.25, "2026-01-14")
        self.response("a", 4, 0.5, "2026-01-15")
        s = self.stats("--since", "2026-01-15")
        self.assertEqual(s["threads"], 1)
        self.assertEqual(s["spend_usd"], 0.5)
        self.assertEqual(s["spend_by_day_usd"], {"2026-01-15": 0.5})

    def test_since_rejects_other_formats(self):
        r = subprocess.run([sys.executable, STATS, "--since", "yesterday"], env=self.e.env, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)

    def test_empty_root_and_bad_response(self):
        s = self.stats()
        self.assertEqual((s["threads"], s["spend_usd"], s["observed_sessions"]), (0, 0, 0))
        self.e.write_thread("a", turns(1))
        d = os.path.join(self.e.tdir("a"), "steps")
        os.makedirs(d)
        open(os.path.join(d, "t0002.response.json"), "w").write("not json")
        self.assertEqual(self.stats()["spend_usd"], 0)


class Grep(unittest.TestCase):
    def setUp(self):
        self.e = Env().init()

    def tearDown(self):
        self.e.cleanup()

    def test_grep(self):
        self.e.write_thread("a", "## you · t1\nfind q11 here\nEND\n")
        self.e.write_thread("b", "## you · t1\nnothing\nEND\n")
        os.makedirs(os.path.join(self.e.root, "threads", "_observed", "p-1"))
        open(os.path.join(self.e.root, "threads", "_observed", "p-1", "thread.md"), "w").write("q11\n")
        r = subprocess.run(["sh", GREP, "q11"], env=self.e.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("threads/a/thread.md", r.stdout)
        self.assertNotIn("_observed", r.stdout)
        self.assertEqual(len(r.stdout.strip().split("\n")), 1)
        r = subprocess.run(["sh", GREP, "zzzznomatch"], env=self.e.env, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (1, ""))


if __name__ == "__main__":
    unittest.main()
