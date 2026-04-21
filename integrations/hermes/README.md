# Hermes Local HuntFlow Integration

Hermes can use HuntFlow on the same Mac through its local terminal tool.

Official Hermes references:

- [Configuration](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md)
- [Add Custom Tools](https://hermes-agent.ai/how-to/add-tools-to-hermes)

Those docs state:

- Hermes config lives under `~/.hermes/`
- the terminal backend can be local
- Hermes can use shell tools, HTTP API tools, or MCP servers

## Recommended setup

1. Start HuntFlow locally:

```bash
cd /Users/na/na/xcode/HunterAgent
npm run local:start:api
```

2. Export HuntFlow credentials for Hermes:

```bash
eval "$(python3 /Users/na/na/xcode/HunterAgent/scripts/local_login.py --shell)"
```

3. Configure Hermes to use local terminal execution and this repo as the working directory.

## Minimal Hermes config snippet

Add the equivalent of this to `~/.hermes/config.yaml`:

```yaml
terminal:
  backend: local

platform_toolsets:
  cli: [terminal, file, skills]
```

Run Hermes from this repo when you want the current directory to be the HuntFlow workspace:

```bash
cd /Users/na/na/xcode/HunterAgent
hermes
```

## Commands Hermes can run

Use these local terminal commands:

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
