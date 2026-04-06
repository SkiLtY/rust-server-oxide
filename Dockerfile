# =============================================================================
# Rust Dedicated Server + Oxide Mod
# Built nightly via GitHub Actions, pushed to ghcr.io/skilty/rust-server-oxide
#
# Multi-stage build:
#   1. Install Rust server from Steam
#   2. Download latest Oxide mod
#   3. Combine into final image
# =============================================================================

# --- Stage 1: Install Rust server from Steam ---
FROM steamcmd/steamcmd:debian-trixie AS install-stage

RUN steamcmd +force_install_dir /srv/rust +login anonymous +app_update 258550 validate +quit

# --- Stage 2: Download latest Oxide mod ---
FROM debian:trixie-slim AS oxide-stage
ARG OXIDE_ZIP_FILE_URL

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    wget \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/oxide

RUN wget ${OXIDE_ZIP_FILE_URL} -O oxide.zip && unzip oxide.zip

# --- Stage 3: Final image ---
FROM debian:trixie-slim AS production-image

# Create unprivileged user
RUN groupadd -g 10001 rust && \
    useradd -r -u 10001 -g rust --create-home rust

# Runtime dependencies
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    ca-certificates \
    netcat-traditional \
    gettext-base \
    libgdiplus \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/rust

RUN chown -R rust:rust /srv/rust

# Copy Rust server
COPY --from=install-stage --chown=rust:rust /srv/rust /srv/rust

# Copy Oxide mod overlay
COPY --from=oxide-stage --chown=rust:rust /tmp/oxide/RustDedicated_Data /srv/rust/RustDedicated_Data/

# Copy entrypoint
COPY --chown=rust:rust runds.sh /srv/rust/runds.sh
RUN chmod +x /srv/rust/runds.sh && mkdir -p /srv/rust/server && chown -R rust:rust /srv/rust/server

# server.port, rcon.port udp, rcon.port tcp, queryport, app.port
EXPOSE 28015/udp 28016/udp 28016/tcp 28017/udp 28082/tcp

USER 10001

ENTRYPOINT ["/srv/rust/runds.sh"]
