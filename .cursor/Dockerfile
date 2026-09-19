FROM node:20-bookworm-slim

# ca-certificates required for git HTTPS clone in Cloud Agent workspace setup
# (build log bld-1310fd83: "CAfile: none" without this package)
# python3* added for the notebook layer (D-W7-JUPYTER) so Cloud Agents can run notebooks/.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV GIT_SSL_CAINFO=/etc/ssl/certs/ca-certificates.crt

# No project COPY. Cursor manages the workspace.
# No npm install — the Node core has zero dependencies (AGENTS.md §2).
# Notebook deps (requirements.txt) are installed on demand, not baked at build time.
