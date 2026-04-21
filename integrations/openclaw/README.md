# OpenClaw Local HuntFlow Integration

OpenClaw can use HuntFlow on the same Mac through its local terminal tool or shell environment.

Official OpenClaw configuration docs:

- [Configuration](https://docs.openclaw.ai/gateway/configuration)

That config reference states:

- OpenClaw reads env vars from the parent process, local `.env`, and `~/.openclaw/.env`
- config lives at `~/.openclaw/openclaw.json`

## Recommended setup

1. Start HuntFlow locally:

```bash
cd /Users/na/na/xcode/HunterAgent
npm run local:start:api
```

2. Export HuntFlow access for OpenClaw:

```bash
eval "$(python3 /Users/na/na/xcode/HunterAgent/scripts/local_login.py --shell)"
```

3. Put these env vars into `~/.openclaw/.env` if you want them to persist:

```bash
HUNTFLOW_API_URL=http://127.0.0.1:8000
HUNTFLOW_EMAIL=owner@huntflow.local
HUNTFLOW_PASSWORD=hunter-owner
```

4. Make sure the OpenClaw agent has terminal access and points at this repo as its workspace.

## Minimal config snippet

Put the equivalent of this into `~/.openclaw/openclaw.json`:

```json5
{
  agents: {
    defaults: {
      workspace: "/Users/na/na/xcode/HunterAgent"
    }
  }
}
```

## Commands OpenClaw can run

All of these are local terminal commands:

```bash
python3 /Users/na/na/xcode/HunterAgent/scripts/huntflow_local_cli.py health
python3 /Users/na/na/xcode/HunterAgent/scripts/huntflow_local_cli.py dashboard
python3 /Users/na/na/xcode/HunterAgent/scripts/huntflow_local_cli.py today
python3 /Users/na/na/xcode/HunterAgent/scripts/huntflow_local_cli.py create-client --name "Northstar" --industry "Fintech"
python3 /Users/na/na/xcode/HunterAgent/scripts/huntflow_local_cli.py create-job --client-id client_x --title "CFO" --must-have finance
python3 /Users/na/na/xcode/HunterAgent/scripts/huntflow_local_cli.py import-candidate --job-order-id job_x --full-name "Lina Chen" --resume-text "Fintech CFO"
python3 /Users/na/na/xcode/HunterAgent/scripts/huntflow_local_cli.py score job_x candidate_y
python3 /Users/na/na/xcode/HunterAgent/scripts/huntflow_local_cli.py draft job_x candidate_y
```
