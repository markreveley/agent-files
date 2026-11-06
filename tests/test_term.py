import json, os, shutil, subprocess, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(__file__))
from helpers import REPO

TERM = os.path.join(REPO, "bin", "agent-files-term")
NVIM = shutil.which("nvim")


@unittest.skipUnless(NVIM, "nvim not on PATH")
class Term(unittest.TestCase):
    """agent-files-term against a headless Neovim with agents.term loaded and two terminals."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="af-term-")
        self.sock = os.path.join(self.tmp, "nvim.sock")
        init = os.path.join(self.tmp, "init.lua")
        with open(init, "w") as f:
            f.write(
                "vim.opt.rtp:prepend(%r)\n"
                "local T = require('agents.term')\n"
                "T.opts.harnesses = {'cat'}\n"
                "vim.fn.jobstart({'cat'}, {term = true})\n"
                "vim.cmd('enew')\n"
                "vim.fn.jobstart({'sh'}, {term = true})\n" % os.path.join(REPO, "nvim"))
        self.nvim = subprocess.Popen([NVIM, "--headless", "--clean", "--listen", self.sock, "-u", init],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            if os.path.exists(self.sock):
                break
            time.sleep(0.05)

    def tearDown(self):
        self.nvim.kill()
        self.nvim.wait()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def term(self, *args, stdin=None):
        env = dict(os.environ, NVIM=self.sock)
        return subprocess.run([sys.executable, TERM, *args], env=env, input=stdin, capture_output=True, text=True)

    def terminals(self):
        r = self.term("ls", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        return {t["harness"] or os.path.basename(t["cmd"]): t for t in json.loads(r.stdout)}

    def test_ls_send_capture(self):
        ts = self.terminals()
        self.assertEqual(ts["cat"]["harness"], "cat")
        self.assertIsNone(ts["sh"]["harness"])
        self.assertNotIn("policy", ts["cat"])
        sh = str(ts["sh"]["buf"])

        r = self.term("ls")
        self.assertEqual(r.returncode, 0, r.stderr)
        row = next(l.split() for l in r.stdout.splitlines() if l.split()[0] == str(ts["cat"]["buf"]))
        # buffer, harness, command: no policy column
        self.assertEqual(len(row), 3, row)
        self.assertEqual(row[1], "cat")
        self.assertEqual(os.path.basename(row[2]), "cat")

        # a send from here to a harness's terminal is typed in like any other
        r = self.term("send", "cat", "hello from an agent")
        self.assertEqual(r.returncode, 0, r.stderr)
        for _ in range(60):
            if any("hello from an agent" in l for l in self.term("capture", "cat").stdout.splitlines()):
                break
            time.sleep(0.05)
        self.assertTrue(any("hello from an agent" in l for l in self.term("capture", "cat").stdout.splitlines()))

        # quotes of both kinds survive the trip; the output line differs from the echoed input
        r = self.term("send", sh, "-", stdin="printf '%s\\n' \"it's \\\"quoted\\\"\"\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        want = 'it\'s "quoted"'
        for _ in range(60):
            lines = [l.strip() for l in self.term("capture", sh).stdout.splitlines()]
            if want in lines:
                break
            time.sleep(0.05)
        self.assertIn(want, lines)
        r = self.term("capture", sh, "-n", "1")
        self.assertEqual(len(r.stdout.rstrip("\n").split("\n")), 1)

    def test_errors(self):
        r = self.term("capture", "nope")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no terminal matches", r.stderr)
        env = dict(os.environ)
        env.pop("NVIM", None)
        r = subprocess.run([sys.executable, TERM, "ls"], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        r = subprocess.run([sys.executable, TERM, "--server", os.path.join(self.tmp, "absent"), "ls"],
                           env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
