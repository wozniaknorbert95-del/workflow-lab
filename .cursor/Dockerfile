FROM node:20-bookworm-slim

# ca-certificates required for git HTTPS clone in Cloud Agent workspace setup
# (build log bld-1310fd83: "CAfile: none" without this package)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV GIT_SSL_CAINFO=/etc/ssl/certs/ca-certificates.crt

# No project COPY. Cursor manages the workspace.
# No npm install — this lab has zero dependencies (AGENTS.md §2).
