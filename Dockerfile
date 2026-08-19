# --- Stage 1: Fetch the Funnel binary ---
FROM alpine:3.18 AS fetcher
RUN apk add --no-cache curl tar perl-utils
ENV FUNNEL_VERSION=0.11.12
WORKDIR /workspace
RUN curl -fsSL https://raw.githubusercontent.com/calypr/funnel/develop/install.sh | sh -s -- v${FUNNEL_VERSION} /workspace

# --- Stage 2: Final Image with Docker CLI ---
FROM ubuntu:22.04

# Install the standard Docker CLI tools and root certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy the Funnel binary into the standard path
COPY --from=fetcher /workspace/funnel /usr/local/bin/funnel
RUN chmod +x /usr/local/bin/funnel

EXPOSE 8000
EXPOSE 9090

# Run out-of-the-box defaults (defaults to the local backend)
ENTRYPOINT ["funnel", "server", "run"]
