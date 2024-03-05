import os
import signal
import gradio as gr

def main():
    WebUI().start()

class WebUI:
    def __init__(self):
        self.restart = False
        self.prevent_inbrowser = False

    def start(self):
        while True:
            app = self.create_ui()
            app.launch(inbrowser = True,
                        server_name = "0.0.0.0",
                        server_port = 7862,
                        prevent_thread_lock=False, quiet=True)

    def create_ui(self):
        with gr.Blocks(analytics_enabled=False,
                        title="Image Test") as app:
            with gr.Row():
                image1 = gr.SimpleImage(label="interactive=False", sources=["upload"], height=512, interactive=False)
                image2 = gr.Image(label="interactive=True", sources=["upload"], height=512, interactive=True)
            text = gr.Textbox(max_lines=1, placeholder="Path to image file")
            button = gr.Button(value="View Image")

            button.click(self.button_click, inputs=text, outputs=[image1, image2])
        return app

    def button_click(self, text):
        return text, text

def sigint_handler(sig, frame):
    os._exit(0)
signal.signal(signal.SIGINT, sigint_handler)

if __name__ == '__main__':
    main()