"""lib/agent_files/git.py: commits from concurrent turns all land."""
import os, shutil, sys, tempfile, threading, unittest
sys.path.insert(0, os.path.dirname(__file__))
import helpers  # noqa: F401  (puts lib/ on sys.path)
from agent_files import git


class Commit(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="af-git-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        git.init(self.root)
        open(os.path.join(self.root, "seed"), "w").close()
        git.run(self.root, "add", "seed")
        git.run(self.root, "commit", "-q", "-m", "init")

    def count(self):
        return int(git.run(self.root, "rev-list", "--count", "HEAD").stdout)

    def test_concurrent_commits_all_land(self):
        n = 12
        for i in range(n):
            os.makedirs(os.path.join(self.root, f"t{i}"))
            with open(os.path.join(self.root, f"t{i}", "thread.md"), "w") as f:
                f.write(f"thread {i}\n")
        results = [None] * n
        go = threading.Barrier(n)

        def one(i):
            go.wait()
            results[i] = git.commit(self.root, [f"t{i}/thread.md"], f"send t{i}", {"Agent-Files-Event": "send"})

        threads = [threading.Thread(target=one, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(self.count(), n + 1)
        self.assertEqual(results, [None] * n)
        self.assertEqual(git.run(self.root, "status", "--porcelain").stdout, "")

    def test_nothing_to_commit_is_not_an_error(self):
        self.assertIsNone(git.commit(self.root, ["seed"], "noop"))
        self.assertIsNone(git.commit(self.root, ["missing"], "noop"))
        self.assertEqual(self.count(), 1)

    def test_failure_is_returned(self):
        open(os.path.join(self.root, ".git", "index.lock"), "w").close()
        with open(os.path.join(self.root, "seed"), "w") as f:
            f.write("changed\n")
        err = git.commit(self.root, ["seed"], "blocked")
        self.assertIn("index.lock", err)


if __name__ == "__main__":
    unittest.main()
