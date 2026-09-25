"""Very simple web UI: `python -m agent.web`, then open http://localhost:8000"""
import html

from flask import Flask, request

from agent.config import configure_logging, settings
from agent.observability import Observability
from agent.service import ask

configure_logging(settings.log_level)

app = Flask(__name__)

PAGE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Simple Agent</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; max-width: 640px; margin: 3rem auto; padding: 0 1rem; color: #1a1a1a; }}
    h1 {{ font-size: 1.4rem; }}
    form {{ display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }}
    input[type=text] {{ flex: 1; padding: 0.6rem; font-size: 1rem; border: 1px solid #ccc; border-radius: 6px; }}
    button {{ padding: 0.6rem 1.2rem; font-size: 1rem; border: none; border-radius: 6px; background: #2563eb; color: white; cursor: pointer; }}
    button:hover {{ background: #1d4ed8; }}
    .steps {{ background: #f5f5f5; border-radius: 8px; padding: 1rem; font-family: monospace; font-size: 0.9rem; white-space: pre-wrap; margin-bottom: 1rem; }}
    .answer {{ font-size: 1.1rem; padding: 1rem; border-radius: 8px; background: #ecfdf5; border: 1px solid #10b981; }}
    .error {{ padding: 1rem; border-radius: 8px; background: #fef2f2; border: 1px solid #ef4444; }}
    .score {{ color: #666; font-size: 0.85rem; margin-top: 0.4rem; }}
    .examples {{ color: #666; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <h1>Simple Agent</h1>
  <form method="post">
    <input type="text" name="question" placeholder="Ask a math or time question..." value="{question}" autofocus>
    <button type="submit">Ask</button>
  </form>
  <p class="examples">Try: "What is 23 * 47 + 10?" or "What time is it?"</p>
  {result}
</body>
</html>"""


def render(question: str = "", result_html: str = "") -> str:
    return PAGE.format(question=html.escape(question), result=result_html)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render()

    question = request.form.get("question", "").strip()
    if not question:
        return render(result_html='<div class="error">Please enter a question.</div>')

    obs = Observability(settings)
    result = ask(question, obs, settings, source="web")

    if result.error:
        return render(question, f'<div class="error">{html.escape(result.error)}</div>')

    steps_text = "\n".join(
        f"[{s.node}] {s.kind.replace('_', ' ')} -> {s.text}" for s in result.steps
    )
    result_html = (
        f'<div class="steps">{html.escape(steps_text)}</div>'
        f'<div class="answer">{html.escape(result.final_answer)}'
        f'<div class="score">correctness: {result.score} - {html.escape(result.comment)}</div></div>'
    )
    return render(question, result_html)


def main():
    app.run(host="0.0.0.0", port=8000, debug=False)


if __name__ == "__main__":
    main()
