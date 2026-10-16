"""Hugging Face Space entry point."""
import os
import sys
from pathlib import Path

# The Space runs from a checkout of this repo, not an installed package.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gfra.app import CSS, THEME, RateLimiter, build_demo, head_script  # noqa: E402
from gfra.demo_view import PDF_DIR, samples  # noqa: E402
from gfra.financebench_eval import judge  # noqa: E402
from gfra.app_factory import build_researcher  # noqa: E402

if os.getenv("SPACE_ID"):  # set by Hugging Face on a Space
    import spaces

    @spaces.GPU
    def _zero_gpu_placeholder():
        """ZeroGPU hardware refuses to start without a GPU function; the agent runs on CPU and calls OpenAI."""


# One request at a time: Progent keeps the policy in module globals.
# The demo answers with gpt-4o-mini (MODEL), the model the ablation and the recorded cases were measured on.
demo = build_demo({True: build_researcher(guarded=True), False: build_researcher(guarded=False)},
                  RateLimiter(5, max_total=100),
                  judge=judge)
demo.queue(default_concurrency_limit=1)

if __name__ == "__main__":
    demo.launch(theme=THEME, css=CSS, head=head_script(samples()), allowed_paths=[str(PDF_DIR)])
