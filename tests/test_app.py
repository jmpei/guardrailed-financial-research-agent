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
