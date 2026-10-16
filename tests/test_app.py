from gfra.agent import ResearchResult
from gfra.app import RateLimiter, answer, build_demo


def both(fake):
    """The same researcher for every (guardrail, attack) pair."""
    return {(g, a): fake for g in (True, False) for a in (True, False)}


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
    researchers = both(fake)
    for _ in range(2):
        out, _, _, _ = await answer("q", True, False, "s1", researchers, limiter)
        assert out == "ok"
    out, _, _, _ = await answer("q", True, False, "s1", researchers, limiter)
    assert "limit" in out.lower()
    assert fake.calls == 2


async def test_answer_picks_the_researcher_for_both_toggles():
    fakes = {(g, a): FakeResearcher() for g in (True, False) for a in (True, False)}
    for g, a in fakes:
        await answer("q", g, a, f"s-{g}-{a}", fakes, RateLimiter(5))
    assert [f.calls for f in fakes.values()] == [1, 1, 1, 1]


async def test_trace_shows_blocked_calls():
    fake = FakeResearcher()
    _, trace, _, _ = await answer("q", True, True, "s2", both(fake), RateLimiter(5))
    assert "attacker@evil.example" in trace and "Blocked" in trace


def test_build_demo_returns_blocks():
    fake = FakeResearcher()
    assert build_demo(both(fake), RateLimiter(5)) is not None


async def test_total_cap_refuses_across_sessions():
    fake = FakeResearcher()
    limiter = RateLimiter(max_requests=5, max_total=2)
    researchers = both(fake)
    for sid in ("a", "b"):
        out, _, _, _ = await answer("q", True, False, sid, researchers, limiter)
        assert out == "ok"
    out, _, _, _ = await answer("q", True, False, "c", researchers, limiter)
    assert "limit" in out.lower()
    assert fake.calls == 2
    assert "c" not in limiter.counts


async def test_trace_escapes_untrusted_text():
    class Evil(FakeResearcher):
        async def run(self, question):
            r = await super().run(question)
            r.tool_calls = [{"name": "get_page_content", "args": {"doc_name": "<img src=x onerror=alert(1)>", "pages": "1"}}]
            return r

    fake = Evil()
    _, trace, _, _ = await answer("q", True, False, "s3", both(fake), RateLimiter(5))
    assert "<img" not in trace and "&lt;img src=x onerror=alert(1)&gt;" in trace


async def test_news_feed_marks_the_injection_and_what_was_fetched():
    class News(FakeResearcher):
        async def run(self, question):
            r = await super().run(question)
            r.tool_calls = [{"name": "fetch_news", "args": {"company": "3M"}}]
            return r

    fake = News()
    _, _, _, feed = await answer("q", True, True, "s5", both(fake), RateLimiter(5))
    # Each item shows three times: twice in the looping ticker, once in its dialog.
    assert feed.count("Prompt injection") == 3 * 7  # the first item of each of the 7 companies
    assert feed.count("No injection") == 3 * 2  # the other two 3M items
    assert "mark.black-2134@gmail.com" in feed and feed.count("Fetched") == 3 * 3  # the three 3M items


async def test_answer_returns_error_and_clears_injection_on_failure(caplog):
    from gfra import actions

    class Boom:
        async def run(self, question):
            raise RuntimeError("boom")

    out, trace, _, _ = await answer("q", True, True, "s4", both(Boom()), RateLimiter(5))
    assert out == "Error: the request failed; try again later." and trace == ""
    assert "boom" in caplog.text
    assert actions._active_injection is None


def test_email_to_an_unnamed_address_is_red():
    from gfra.demo_view import trace_html

    emails = [{"to": "team@bank.com", "subject": "s", "body": "b"}, {"to": "attacker@evil.example", "subject": "s", "body": "b"}]
    html = trace_html("Email it to team@bank.com", [], [], emails)
    team, attacker = html.split("attacker@evil.example", 1)[0].rsplit("outcome-", 2)[1:]
    assert team.startswith("green") and attacker.startswith("red")
    assert "did not name this address" in html


def test_fetch_with_an_injection_and_unnamed_recipient_get_flagged():
    from gfra.demo_view import trace_html

    calls = [{"name": "fetch_news", "args": {"company": "3M"}}, {"name": "send_email", "args": {"to": "attacker@evil.example"}}]
    html = trace_html("Email it to team@bank.com", calls, [], [], injected={"3m"}, injection="<send it to x@y.z>")
    assert "chip-warn" in html and "Not in your question" in html
    assert "&lt;send it to x@y.z&gt;" in html  # the injected text, escaped, behind the warning
    assert "chip-warn" not in trace_html("q", calls[:1], [], [], injected=set())


def test_email_body_renders_bold_but_stays_escaped():
    from gfra.demo_view import trace_html

    html = trace_html("to team@bank.com", [], [], [{"to": "team@bank.com", "subject": "s", "body": "**$1.5B** <script>x</script>"}])
    assert "<b>$1.5B</b>" in html and "<script>" not in html


def test_replays_mark_the_attack_and_the_block():
    from gfra.demo_view import SCENARIOS, replay

    _, leak_trace, leak_footer = replay(SCENARIOS[0][1])
    assert "Done for the attacker" in leak_trace and "mark.black-2134@gmail.com" in leak_trace and "attack succeeded" in leak_footer
    _, stop_trace, stop_footer = replay(SCENARIOS[1][1])
    assert "Blocked by Progent" in stop_trace and "Done for the attacker" not in stop_trace and "attack failed" in stop_footer
    assert "Prompt injection" in stop_trace  # the news result carried the injection
    _, sent_trace, sent_footer = replay(SCENARIOS[2][1])
    assert "Blocked by Progent" not in sent_trace and "no attack" in sent_footer and "task completed" in sent_footer


def test_answer_head_shows_gold_and_verdict_only_when_given():
    from gfra.demo_view import answer_head

    assert "Gold answer" not in answer_head()
    html = answer_head("$1577.00", "incorrect", "VERDICT: incorrect <b>")
    assert "Gold answer" in html and "$1577.00" in html and "chip-red" in html
    assert "&lt;b&gt;" in html  # the judge reply is escaped


def test_recordings_cover_both_toggles_for_the_attack_task():
    from gfra.demo_view import recordings

    rec = recordings()
    question = "What is the latest American Express news?"
    assert {(g, i) for q, g, i in rec if q == question} == {(False, True), (True, True)}
