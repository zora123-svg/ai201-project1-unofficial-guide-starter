"""
Milestone 5: query interface for the Unofficial Guide.

A Gradio web UI over the grounded-generation pipeline. Type a question about
off-campus housing near University of St. Thomas; the app retrieves relevant
chunks, generates an answer grounded in them, and shows which documents the
answer drew from.

Run with:
    python app.py
Then open http://localhost:7860
"""

import gradio as gr

from src.generate import ask


def handle_query(question: str):
    """Run one question through the pipeline and format it for the UI."""
    question = (question or "").strip()
    if not question:
        return "Please enter a question.", ""

    result = ask(question)
    if result["sources"]:
        sources = "\n".join(f"• {s}" for s in result["sources"])
    else:
        sources = "(no sources — the guide didn't have enough information)"
    return result["answer"], sources


EXAMPLES = [
    "How long does a landlord have to return my security deposit in Minnesota?",
    "What is the Student Tenant Education Program (STEP)?",
    "What do people say about renting in the Midway area of St. Paul?",
    "Which apartments are close to the University of St. Thomas campus?",
]

with gr.Blocks(title="Unofficial Guide — UST Off-Campus Housing") as demo:
    gr.Markdown(
        "# 🏠 Unofficial Guide — Off-Campus Housing near University of St. Thomas\n"
        "Ask about neighborhoods, apartments, leases, deposits, and tenant "
        "rights in St. Paul. Answers come **only** from collected documents "
        "(university pages, Minnesota tenant law, Reddit, reviews) and cite "
        "their sources. If the guide doesn't cover something, it will say so."
    )
    with gr.Row():
        inp = gr.Textbox(
            label="Your question",
            placeholder="e.g. How long does a landlord have to return my deposit?",
            scale=4,
        )
        btn = gr.Button("Ask", variant="primary", scale=1)

    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)

    gr.Examples(examples=EXAMPLES, inputs=inp)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])


if __name__ == "__main__":
    demo.launch()
