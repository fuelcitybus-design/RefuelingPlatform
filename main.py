from fastapi import FastAPI
import gradio as gr

app = FastAPI()

def hello(name):
    return f"Hello {name}"

with gr.Blocks() as demo:
    name = gr.Textbox()
    out = gr.Textbox()
    btn = gr.Button("Run")
    btn.click(hello, inputs=name, outputs=out)

app = gr.mount_gradio_app(app, demo, path="/")
