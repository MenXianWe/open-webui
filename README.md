# QLCodeChat

QLCodeChat is a private AI web application customized for QLCodeAPI.

Official site: https://qlcodeapi.com/

Default OpenAI-compatible API endpoint:

```text
https://api.qlcodeapi.com/v1
```

## Development

Frontend development:

```bash
npm run dev
```

Backend development:

```bash
cd backend
./dev.sh
```

## Build

```bash
npm run build
```

## Docker

The application is intended to run as a private deployment with persistent backend data mounted at:

```text
/app/backend/data
```

Keep runtime secrets, API keys, database URLs, and storage credentials outside source control.

Default deployment:

```bash
QLCODE_CHAT_SECRET_KEY='replace-with-a-long-random-secret' docker compose up -d --build
```

The service listens on host port `3000` by default. Override it with:

```bash
QLCODE_CHAT_PORT=8080 QLCODE_CHAT_SECRET_KEY='replace-with-a-long-random-secret' docker compose up -d --build
```

Check the running service:

```bash
docker compose ps
curl -i http://127.0.0.1:3000/health
```

For server deployment, use the production compose file and the detailed guide:

```text
docker-compose.prod.yaml
docs/QLCodeChat-Usage-Deploy.md
```

## Maintenance

This branch contains private QLCode customizations. Keep changes concentrated and documented so future maintenance, review, and deployment stay predictable.
