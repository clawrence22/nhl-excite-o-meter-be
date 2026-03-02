# NHL Excite‑o‑Meter Backend

## Project Structure
```
nhl-excite-o-meter-be/
├── backend/           # Flask API
│   ├── main
│   ├── exciteo/
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yaml
└── runLocal.sh
```

## Local Dev
```bash
bash runLocal.sh
```

- API: http://localhost:5001

## Test
```bash
curl http://localhost:5001/healthz
curl http://localhost:5001/excitement/2023020204
curl "http://localhost:5001/excitement/batch?ids=2023020204,2023020205"
```

## Notes
- Uses **api-web** PBP endpoint only (no statsapi).
- Recency decay uses event order (configurable via `EVENT_SPACING_SEC` in `exciteo/config.py`).
- Tuning knobs live in `exciteo/config.py`.
- Core math is in `exciteo/scoring.py`; NHL client & cache are in `exciteo/nhl_client.py`.