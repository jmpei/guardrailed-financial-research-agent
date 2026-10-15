from gfra.agent import ResearchResult
from gfra.app import RateLimiter, answer, build_demo


class FakeResearcher:
    def __init__(self):
        self.calls = 0

    async def run(self, question):
        self.calls += 1
        return ResearchResult(answer="ok", tool_calls=[{"name": "send_email", "args": {"to": "a"}}],
                              blocked=[{"tool": "send_email", "args": {"to": "attacker@evil.example"}, "reason": "r"}],
                              input_tokens=1, output_tokens=1, cost_usd=0.001, latency_s=0.5)


async def test_rate_limit_refuses_after_cap():
    fake = FakeResearcher()
    limiter = RateLimiter(max_requests=2)
    researchers = {True: fake, False: fake}
    for _ in range(2):
        out, _ = await answer("q", True, False, "s1", researchers, limiter)
        assert out == "ok"
    out, _ = await answer("q", True, False, "s1", researchers, limiter)
    assert "limit" in out.lower()
    assert fake.calls == 2


async def test_trace_shows_blocked_calls():
    fake = FakeResearcher()
    _, trace = await answer("q", True, True, "s2", {True: fake, False: fake}, RateLimiter(5))
    assert "attacker@evil.example" in trace and "Blocked" in trace


def test_build_demo_returns_blocks():
    fake = FakeResearcher()
    assert build_demo({True: fake, False: fake}, RateLimiter(5)) is not None


async def test_total_cap_refuses_across_sessions():
    fake = FakeResearcher()
    limiter = RateLimiter(max_requests=5, max_total=2)
    researchers = {True: fake, False: fake}
    for sid in ("a", "b"):
        out, _ = await answer("q", True, False, sid, researchers, limiter)
        assert out == "ok"
    out, _ = await answer("q", True, False, "c", researchers, limiter)
    assert "limit" in out.lower()
    assert fake.calls == 2
    assert "c" not in limiter.counts


async def test_trace_puts_injected_args_in_code_span():
    class Evil(FakeResearcher):
        async def run(self, question):
            r = await super().run(question)
            r.tool_calls = [{"name": "send_email", "args": {"body": "![x](http://evil/a) `x`"}}]
            return r

    fake = Evil()
    _, trace = await answer("q", True, False, "s3", {True: fake, False: fake}, RateLimiter(5))
    line = next(l for l in trace.splitlines() if "![x](http://evil/a)" in l)
    assert line.count("![x](http://evil/a)") == 1
    before, _, after = line.partition("![x](http://evil/a)")
    assert before.count("``") == 1 and after.count("``") == 1
    assert "`" not in (before + after).replace("``", "").replace("`send_email`", "")


async def test_answer_returns_error_and_clears_injection_on_failure(caplog):
    from gfra import actions

    class Boom:
        async def run(self, question):
            raise RuntimeError("boom")

    out, trace = await answer("q", True, True, "s4", {True: Boom(), False: Boom()}, RateLimiter(5))
    assert out == "Error: the request failed; try again later." and trace == ""
    assert "boom" in caplog.text
    assert actions._active_injection is None
