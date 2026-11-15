"""Entry point for a Hugging Face Gradio-SDK Space."""
import os
import socket

import gradio as gr
import uvicorn

from app.main import app as api

# ZeroGPU hardware refuses to start an app with no @spaces.GPU function. This placeholder
# satisfies that check; it is never called and uses no GPU.
try:
    import spaces

    @spaces.GPU
    def _unused():
        return None
except ImportError:
    pass

with gr.Blocks(title="Earth System Trend Detective API") as ui:
    gr.Markdown("# Earth System Trend Detective API\nSee `/docs` for the endpoints.")

app = gr.mount_gradio_app(api, ui, path="/ui")


def _port_in_use(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    if not _port_in_use(port):
        uvicorn.run(app, host="0.0.0.0", port=port)