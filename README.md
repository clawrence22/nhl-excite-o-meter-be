# NHL Excite-o-Meter Backend

Backend service that generates NHL game excitement previews and scores.

**Structure**
```
nhl-excite-o-meter-be/
├── src/nhl_excite_o_meter/   # Application package
├── tests/                    # Pytest suite
├── iac/                      # Terraform stacks
├── Dockerfile
├── docker-compose.yaml
├── pyproject.toml
└── runLocal.sh
```

**Requirements**
- Python 3.11+
- Docker or Podman (optional)
- AWS credentials if accessing RDS with IAM auth

**Environment Variables**
- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_NAME`
- `DB_REGION`
- `DB_SSLMODE`

**Local Setup**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

**Run Locally**
```bash
python -m nhl_excite_o_meter
```

**Run With Podman Compose**
```bash
bash runLocal.sh
```

**Run With Docker**
```bash
docker build -t nhl-excite-o-meter-be .
docker run --rm -p 5001:5001 \
  -e DB_HOST=... \
  -e DB_PORT=5432 \
  -e DB_USER=... \
  -e DB_NAME=... \
  -e DB_REGION=us-east-1 \
  -e DB_SSLMODE=require \
  nhl-excite-o-meter-be
```

**Health Check**
```bash
curl http://localhost:5001/healthz
```

**Tests**
```bash
python -m pytest -q
```

**Notes**
- The API pulls NHL data from the `api-web` play-by-play endpoint.
- Preview scoring is implemented in `src/nhl_excite_o_meter/preview_excitement_score.py`.
