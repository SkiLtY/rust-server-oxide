# rust-server-oxide

Automated Docker image build for Rust dedicated game server with [Oxide](https://oxidemod.com/) mod support.

Built nightly via GitHub Actions, pushed to `ghcr.io/skilty/rust-server-oxide:latest`.

## How it works

Multi-stage Dockerfile:
1. **Steam stage** — downloads latest Rust server via SteamCMD
2. **Oxide stage** — downloads latest Oxide mod release from GitHub
3. **Production stage** — combines both on a minimal Debian base

GitHub Actions runs nightly at 02:00 UTC. Images are tagged `latest` and `YYYY-MM-DD`.

## Usage

```yaml
services:
  rust:
    image: ghcr.io/skilty/rust-server-oxide:latest
    command:
      - +server.port "28015"
      - +server.queryport "28017"
      - +rcon.port "28016"
      - +rcon.web "1"
      - +rcon.password "changeme"
      - +server.hostname "My Server"
      - +server.worldsize "4000"
      - +server.maxplayers "8"
    volumes:
      - ./data/server:/srv/rust/server
      - ./data/oxide:/srv/rust/oxide
    ports:
      - "28015:28015/udp"
      - "28017:28017/udp"
      - "28016:28016/tcp"
```

## Manual build

```bash
# Get latest Oxide URL
OXIDE_URL=$(curl -s https://api.github.com/repos/OxideMod/Oxide.Rust/releases/latest \
  | python3 -c "import sys,json; assets=json.load(sys.stdin)['assets']; print([a['browser_download_url'] for a in assets if 'linux' in a['name'].lower()][0])")

# Build
docker build --build-arg OXIDE_ZIP_FILE_URL="$OXIDE_URL" -t rust-server-oxide .
```

## Credits

Based on [max-pfeiffer/rust-game-server-docker](https://github.com/max-pfeiffer/rust-game-server-docker).
