import json, os, subprocess, sys, tempfile, shutil, unittest
sys.path.insert(0, os.path.dirname(__file__))
from helpers import REPO

HOOK = os.path.join(REPO, "bin", "agent-files-hook")
SID = "ABCDEF1234567890"


class Hook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "threads"))
        self.env = dict(os.environ, AGENT_FILES_ROOT=self.tmp)
        self.env.pop("AGENT_FILES_RUNNER", None)
        self.dir = os.path.join(self.tmp, "threads", "_observed", "api-abcdef12")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fire(self, name, raw=None, env=None, **kw):
        ev = {"session_id": SID, "transcript_path": "/x/y.jsonl", "cwd": "/Users/m/code/API", "hook_event_name": name, **kw}
        r = subprocess.run([sys.executable, HOOK], input=raw if raw is not None else json.dumps(ev),
                           env=env or self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")
        return r

    def status(self):
        return open(os.path.join(self.dir, "status")).read().strip()

    def test_mapping(self):
        self.fire("SessionStart")
        self.assertEqual(self.status(), "done")
        th = open(os.path.join(self.dir, "thread.md")).read()
        self.assertIn("runtime: observed", th)
        self.assertIn("project: /Users/m/code/API", th)
        for ev, want in [("UserPromptSubmit", "working"), ("PreToolUse", "working"), ("PostToolUse", "working"),
                         ("Stop", "done")]:
            self.fire(ev)
            self.assertEqual(self.status(), want, ev)
        self.fire("UserPromptSubmit")
        self.fire("Notification", notification_type="permission_prompt")
        self.assertEqual(self.status(), "blocked")
        self.fire("Notification", notification_type="idle_prompt")
        self.assertEqual(self.status(), "blocked")        # no change
        self.fire("PostToolUse")
        self.assertEqual(self.status(), "working")

    def test_every_registered_event_is_handled(self):
        # status after each event; None = no change (SessionEnd: directory removed)
        want = {"SessionStart": "done", "UserPromptSubmit": "working", "PreToolUse": "working",
                "PermissionRequest": "blocked", "PostToolUse": "working", "PostToolUseFailure": "working",
                "Notification": None, "Stop": "done", "StopFailure": "failed", "SessionEnd": None}
        events = subprocess.run([sys.executable, HOOK, "--events"], capture_output=True, text=True).stdout.split()
        self.assertEqual(set(events), set(want))
        for ev in events:
            if ev == "SessionEnd":
                continue
            self.fire("SessionStart" if ev != "SessionStart" else "UserPromptSubmit")
            before = self.status()
            self.fire(ev)
            self.assertEqual(self.status(), want[ev] or before, ev)

    def test_permission_request_blocks_at_once(self):
        self.fire("UserPromptSubmit")
        self.fire("PermissionRequest", tool_name="Bash", tool_input={"command": "rm -rf build"})
        self.assertEqual(self.status(), "blocked")
        self.fire("PostToolUseFailure", tool_name="Bash", error="Exit code 1")   # approved, then failed
        self.assertEqual(self.status(), "working")

    def test_stop_failure(self):
        self.fire("UserPromptSubmit")
        self.fire("StopFailure", error="rate_limit", last_assistant_message="API Error: Rate limit reached")
        self.assertEqual(self.status(), "failed")

    def test_notification_without_type_is_ignored(self):
        self.fire("UserPromptSubmit")
        self.fire("Notification", message="Claude needs your permission")
        self.assertEqual(self.status(), "working")

    def test_installer_registers_the_hook_events(self):
        dest = os.path.join(self.tmp, "bin")
        out = subprocess.run(["sh", os.path.join(REPO, "install.sh"), dest], capture_output=True, text=True).stdout
        block = json.loads(out[out.index('{ "hooks"'):out.index("}}") + 2])
        events = subprocess.run([sys.executable, HOOK, "--events"], capture_output=True, text=True).stdout.split()
        self.assertEqual(list(block["hooks"]), events)
        for groups in block["hooks"].values():
            self.assertEqual(groups, [{"hooks": [{"type": "command", "command": "agent-files-hook"}]}])

    def test_session_end_deletes(self):
        self.fire("SessionStart")
        self.assertTrue(os.path.isdir(self.dir))
        self.fire("SessionEnd")
        self.assertFalse(os.path.exists(self.dir))

    def test_runner_env_noop(self):
        self.fire("SessionStart", env=dict(self.env, AGENT_FILES_RUNNER="1"))
        self.assertFalse(os.path.exists(self.dir))

    def test_garbage_input_exit_0(self):
        for raw in ["", "not json", "[]", "null", "{\"hook_event_name\": 5}", "\xff"]:
            self.fire("x", raw=raw)

    def test_observed_log(self):
        self.fire("SessionStart"); self.fire("UserPromptSubmit"); self.fire("PreToolUse"); self.fire("Stop")
        lines = open(os.path.join(self.tmp, "trial", "observed.log")).read().strip().split("\n")
        self.assertEqual([l.split("\t")[2] for l in lines], ["done", "working", "done"])   # PreToolUse: no change

    def test_missing_root_noop(self):
        self.fire("SessionStart", env=dict(self.env, AGENT_FILES_ROOT="/nonexistent/zzz"))


if __name__ == "__main__":
    unittest.main()
