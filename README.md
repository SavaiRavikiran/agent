# agent

Small LangGraph ReAct agent (calculator + clock tools) with full Langfuse
observability: tracing, sessions/users, managed prompts, correctness scoring,
a human-annotation review queue, and dataset-driven experiments.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY / LANGFUSE_* as needed

python -m agent.cli "What is 23 * 47 + 10?"
python -m agent.setup_langfuse   # one-time: seeds prompts/dataset/queue in Langfuse
python -m agent.experiment       # runs the agent against the seeded dataset
```

Without `ANTHROPIC_API_KEY` the agent falls back to a deterministic offline
LLM stub. Without `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY` it runs with
tracing disabled instead of failing.

## Run in Docker

```bash
docker build -t agent:latest .
docker run --rm agent:latest "What is 8 * 8?"

# with Langfuse tracing (Langfuse running on the host):
docker run --rm --env-file .env agent:latest "What is 8 * 8?"
```

When Langfuse runs on the host and the agent runs in Docker Desktop, set
`LANGFUSE_HOST=http://host.docker.internal:3000` in `.env` (not `localhost`).
