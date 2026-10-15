"""Hugging Face Space entry point."""
from gfra.app import RateLimiter, build_demo
from gfra.app_factory import build_researcher

# One request at a time: Progent keeps the policy in module globals.
demo = build_demo({True: build_researcher(guarded=True), False: build_researcher(guarded=False)}, RateLimiter(5))
demo.queue(default_concurrency_limit=1)

if __name__ == "__main__":
    demo.launch()
