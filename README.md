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

## Web UI

```bash
python -m agent.web
```

Open http://localhost:8000, type a question, click Ask. Shows the tool-call
trace and the final answer with its correctness score, same as the CLI.

## Run in Docker

Build the image once, from this directory:

```bash
docker build -t agent:latest .
```

### Web UI

Start it in the background. Leave `LANGFUSE_HOST` in `.env` as
`http://localhost:3000` for runs on the host. The `-e` flags override that
only inside the container, so Docker Desktop can reach Langfuse on the host.

```bash
docker run -d --name agent-web -p 8000:8000 --env-file .env \
  -e LANGFUSE_HOST=http://host.docker.internal:3000 \
  -e LANGFUSE_BASE_URL=http://host.docker.internal:3000 \
  --entrypoint python agent:latest -m agent.web
```

Open http://localhost:8000.

Stop it, then start the same container again:

```bash
docker stop agent-web
docker start agent-web
```

Remove it when you want a fresh container (required after a rebuild):

```bash
docker rm -f agent-web
```

### CLI

One question, then the container exits:

```bash
docker run --rm --env-file .env \
  -e LANGFUSE_HOST=http://host.docker.internal:3000 \
  -e LANGFUSE_BASE_URL=http://host.docker.internal:3000 \
  agent:latest "What is 8 * 8?"
```
