import os, subprocess, sys, tempfile, time, shutil

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "lib"))
RUN = os.path.join(REPO, "bin", "agent-files-run")


class Env:
    """A throwaway data root + state dir."""
    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="af-test-")
        self.root = os.path.join(self.tmp, "root")
        self.state = os.path.join(self.tmp, "state")
        self.env = dict(os.environ, AGENT_FILES_ROOT=self.root, XDG_STATE_HOME=self.state, AGENT_FILES_MOCK_SPEED="1")
        self.env.pop("AGENT_FILES_RUNNER", None)

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run(self, *args, **kw):
        return subprocess.run([sys.executable, RUN, *args], env=kw.pop("env", self.env), capture_output=True, text=True, **kw)

    def popen(self, *args):
        return subprocess.Popen([sys.executable, RUN, *args], env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def init(self):
        r = self.run("init")
        assert r.returncode == 0, r.stderr
        return self

    def tdir(self, tid):
        return os.path.join(self.root, "threads", *tid.split("/"))

    def write_thread(self, tid, body, model="mock/echo", extra=""):
        d = self.tdir(tid)
        os.makedirs(d, exist_ok=True)
        fm = f"---\nagent: default\nruntime: direct\nmodel: {model}\ncontext: replay\nkind: main\n{extra}---\n\n"
        with open(os.path.join(d, "thread.md"), "w") as f:
            f.write(fm + body)
        return os.path.join(d, "thread.md")

    def read(self, tid, name="thread.md"):
        with open(os.path.join(self.tdir(tid), name)) as f:
            return f.read()

    def status(self, tid):
        try:
            return self.read(tid, "status").strip()
        except OSError:
            return None

    def git(self, *a):
        return subprocess.run(["git", "-C", self.root, *a], capture_output=True, text=True).stdout


def wait_for(pred, timeout=10, step=0.05):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(step)
    return False
