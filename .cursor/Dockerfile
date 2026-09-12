FROM node:20-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# No project COPY. Cursor manages the workspace.
# No npm install — this lab has zero dependencies (AGENTS.md §2).
