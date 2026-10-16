"""Container entry point: uvicorn serves the demo built in app.py.

demo.launch() requests its own page with a 3 s timeout and exits if it gets no answer, which happens
on a slow Cloud Run cold start; mounting the demo on a FastAPI app skips that check.
"""
import os

import gradio as gr
import uvicorn
from fastapi import FastAPI

from app import demo  # also puts src/ on sys.path
from gfra.app import CSS, THEME, head_script
from gfra.demo_view import PDF_DIR, samples

app = gr.mount_gradio_app(FastAPI(), demo, path="/", theme=THEME, css=CSS, head=head_script(samples()),
                          allowed_paths=[str(PDF_DIR)])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
