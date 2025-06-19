
import gradio as gr
from tools import simulate
import os

with gr.Blocks() as demo:
    gr.Image("image.png", show_label=False, show_download_button=False,
             show_fullscreen_button=False, height=380)

    with gr.Row():
        n_drop = gr.Dropdown(list(range(3, 11)),
                             label="Número de parejas", value=4)
        mode_drop = gr.Dropdown(["Random", "Utopía", "Distopía"],
                                label="Tipo de preferencias", value="Random")
        btn = gr.Button("Play", variant="primary")

    out_html = gr.HTML()
    btn.click(simulate, inputs=[n_drop, mode_drop], outputs=out_html)

# if __name__ == "__main__":
#     demo.launch()
    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 7860))
        demo.launch(server_name="0.0.0.0", server_port=port)
