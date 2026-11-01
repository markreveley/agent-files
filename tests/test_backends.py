"""Anthropic and OpenAI-compatible backends through the runner, with fake SDKs (tests/fakes)."""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
from helpers import Env
from agent_files import thread as T

FAKES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fakes")
Q = "## you · t1\nhello there\nEND\n"
PRICES = '\n[prices."claude-test"]\ninput = 3.0\noutput = 15.0\ncache_write = 3.75\ncache_read = 0.3\n'


class Backends(unittest.TestCase):
    def setUp(self):
        self.e = Env().init()
        with open(os.path.join(self.e.root, "config.toml"), "a") as f:
            f.write(PRICES)
        self.log = os.path.join(self.e.tmp, "sdk.log")
        pp = os.environ.get("PYTHONPATH")
        self.e.env["PYTHONPATH"] = FAKES + (os.pathsep + pp if pp else "")
        self.e.env["FAKE_SDK_LOG"] = self.log

    def tearDown(self):
        self.e.cleanup()

    def turn(self, model, scenario="end_turn"):
        self.e.write_thread("t", Q, model=model)
        r = self.e.run("once", "t", env=dict(self.e.env, FAKE_SDK_SCENARIO=scenario))
        text = self.e.read("t")
        return r, text, T.parse(text).turns[1]

    def step(self, kind):
        return json.loads(self.e.read("t", f"steps/t0002.{kind}.json"))

    def calls(self):
        with open(self.log) as f:
            return [json.loads(l) for l in f]

    # --- Anthropic ---------------------------------------------------------

    def test_anthropic_ok_escapes_costs_and_caches(self):
        r, text, agent = self.turn("claude-test")
        self.assertEqual(self.e.status("t"), "done", r.stderr)
        self.assertEqual(agent.closed, "ok")
        self.assertIn("\\## you · t9\n\\END", text)          # model text cannot forge a turn or END
        self.assertEqual([t.role for t in T.parse(text).turns], ["you", "agent", "you"])
        resp = self.step("response")
        self.assertEqual(resp["stop_reason"], "end_turn")
        self.assertAlmostEqual(resp["cost_usd"], (1000 * 3 + 500 * 15 + 200 * 3.75 + 300 * 0.3) / 1e6)
        (call,) = self.calls()
        self.assertEqual(call["extra_body"]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(call["model"], "claude-test")

    def test_anthropic_max_tokens(self):
        r, text, agent = self.turn("claude-test", "max_tokens")
        self.assertEqual(self.e.status("t"), "done")
        self.assertIn("! stopped: max_tokens\nEND\n", text)

    def test_anthropic_refusal_is_failed_turn(self):
        r, text, agent = self.turn("claude-test", "refusal")
        self.assertEqual(self.e.status("t"), "failed")
        self.assertIn("! error: refusal (cyber)\nEND (failed)\n", text)
        self.assertEqual(self.step("error")["kind"], "refusal")
        self.assertEqual(self.step("response")["stop_reason"], "refusal")

    def test_anthropic_4xx_fails_immediately(self):
        r, text, agent = self.turn("claude-test", "http_400")
        self.assertEqual(self.e.status("t"), "failed")
        self.assertIn("END (failed)\n", text)
        err = self.step("error")
        self.assertEqual((err["kind"], err["http_status"]), ("api", 400))
        self.assertEqual(len(self.calls()), 1)               # no retry

    def test_anthropic_served_by_other_model(self):
        r, text, agent = self.turn("claude-test", "other_model")
        self.assertIn("! served by claude-other\nEND\n", text)
        resp = self.step("response")
        self.assertEqual(resp["served_model"], "claude-other")
        self.assertEqual(resp["cost_usd"], 0.0)               # priced by the served model, which has no entry
        self.assertIn("no [prices] entry for claude-other", r.stderr)

    # --- OpenAI-compatible -------------------------------------------------

    def test_openai_compat_ok(self):
        r, text, agent = self.turn("ollama/test")
        self.assertEqual(self.e.status("t"), "done", r.stderr)
        self.assertEqual(agent.body, "local reply")
        resp = self.step("response")
        self.assertEqual((resp["cost_usd"], resp["usage"]["input_tokens"]), (0.0, 40))
        (call,) = self.calls()
        self.assertEqual(call["model"], "test")
        self.assertEqual(call["messages"][-1], {"role": "user", "content": "hello there"})

    def test_openai_compat_length_is_max_tokens(self):
        r, text, agent = self.turn("ollama/test", "max_tokens")
        self.assertIn("! stopped: max_tokens\nEND\n", text)

    def test_openai_compat_4xx_fails_immediately(self):
        r, text, agent = self.turn("ollama/test", "http_400")
        self.assertEqual(self.e.status("t"), "failed")
        err = self.step("error")
        self.assertEqual((err["kind"], err["http_status"]), ("api", 400))
        self.assertEqual(len(self.calls()), 1)


if __name__ == "__main__":
    unittest.main()
