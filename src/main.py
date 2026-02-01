import gradio as gr
from rag_retrieval import generate_answer

def format_context(context):
    result = "<h2 style='color: #ff7800;'>Relevant Context</h2>\n\n"
    for doc in context:
        result += f"<span style='color: #ff7800;'>Source: {doc.metadata['source']}</span>\n\n"
        result += doc.page_content + "\n\n"
    return result


def chat(history):
    """History is in messages format: [{"role": "user", "content": "..."}, ...]"""
    if not history:
        return history, ""
    
    last_message = history[-1]["content"]
    prior = history[:-1]
    answer, context = generate_answer(last_message, prior)
    
    # Create new history instead of modifying in place
    new_history = history + [{"role": "assistant", "content": answer}]
    return new_history, format_context(context)

def main():
    def put_message_in_chatbot(message, history):
        return "", history + [{"role": "user", "content": message}]

    theme = gr.themes.Soft(font=["Inter", "system-ui", "sans-serif"])

    with gr.Blocks(title="Best Friend of Beiji", theme=theme) as ui:
        gr.Markdown("# 🏢 Best Friend of Beiji\nAsk me anything about Beiji!")

        with gr.Row():
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(
                        label="💬 Conversation", height=600, type="messages", show_copy_button=True
                    )
                message = gr.Textbox(
                    label="Your Question",
                    placeholder="Ask anything about Beiji...",
                    show_label=False,
                )

            with gr.Column(scale=1):
                context_markdown = gr.Markdown(
                    label="📚 Retrieved Context",
                    value="*Retrieved context will appear here*",
                    container=True,
                    height=600,
                )

        message.submit(
            put_message_in_chatbot, inputs=[message, chatbot], outputs=[message, chatbot]
        ).then(chat, inputs=chatbot, outputs=[chatbot, context_markdown])

    ui.launch(inbrowser=True)

if __name__ == "__main__":
    main()