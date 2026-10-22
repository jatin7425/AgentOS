FROM node:24-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates git \
    && rm -rf /var/lib/apt/lists/*
ARG CLAUDE_CLI_VERSION=latest
ARG CODEX_CLI_VERSION=latest
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CLI_VERSION} @openai/codex@${CODEX_CLI_VERSION}
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY . /app/cli_api
RUN mkdir -p /home/node/.claude /home/node/.codex && chown -R node:node /app /home/node
USER node
ENV HOME=/home/node
EXPOSE 8088
CMD ["python", "-m", "cli_api.docker_start"]
