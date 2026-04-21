# HuntFlow Local Skill

Use the HuntFlow local bridge CLI from Hermes terminal mode.

## Preconditions

- HuntFlow API is running on `127.0.0.1:8000`
- Hermes terminal backend is local
- `HUNTFLOW_API_URL` and `HUNTFLOW_BEARER_TOKEN` are exported, or demo credentials are available

## Preferred commands

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

## Rule

Prefer the bridge CLI over raw curl so Hermes can reason over stable JSON output.
