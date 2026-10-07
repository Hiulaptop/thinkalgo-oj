# ThinkAlgo OJ

ThinkAlgo OJ is a DMOJ/VNOJ-based online judge. The repository is standalone at
<https://github.com/Hiulaptop/thinkalgo-oj>.

## Local stack (one compose command)

The local stack is defined in **one** file, `docker-compose.local.yml`. It
starts the same application processes used in production and provides local
replacements for the services that production keeps outside Compose:

- MariaDB (`db`) with a persistent named volume;
- Redis (`redis`) with AOF persistence;
- RustFS (`r2`) as an S3-compatible local R2 endpoint, plus automatic bucket
  creation (`thinkcode-media` and `thinkcode-problems`);
- Django/uWSGI (`site`), the bridge (`bridged`), Celery (`celery`), and the
  websocket/long-poll daemon (`wsevent`).

There is deliberately no nginx. Django serves static/media in local DEBUG mode,
the site is available directly on port 8000, and websocket traffic is exposed
directly on localhost.

From the repository root, run:

```sh
docker compose -f docker-compose.local.yml up --build --remove-orphans
```

The `site` container runs migrations before starting uWSGI, so a fresh database
is ready without a second startup command. Open <http://localhost:8000/>.

Useful local endpoints:

| Component | URL |
| --- | --- |
| Web site | <http://localhost:8000/> |
| Browser WebSocket | `ws://localhost:15100/` |
| WebSocket long-poll fallback | <http://localhost:15102/channels/> |
| Local R2/S3 API | <http://localhost:9000/> |
| RustFS console | <http://localhost:9001/> (`minioadmin` / `minioadmin`) |
| Bridge Django protocol | `127.0.0.1:9998` |
| Bridge judge protocol | `127.0.0.1:9999` |

The browser websocket URL is configured as `ws://localhost:15100/`; application
containers post events privately to `ws://wsevent:15101/`. This avoids relying
on nginx path proxying while preserving the same event daemon behavior as
production. The HTTP fallback uses `http://localhost:15102/channels/`.

### First local admin account

In another terminal, after the stack is healthy:

```sh
docker compose -f docker-compose.local.yml exec site python3 manage.py createsuperuser
```

Follow logs with `docker compose -f docker-compose.local.yml logs -f site`.
Stop the stack with `docker compose -f docker-compose.local.yml down --remove-orphans`. Named
volumes preserve the database, Redis, MinIO objects, media, and problem data.
To intentionally reset all local data, use `docker compose -f docker-compose.local.yml down -v`.

## Cloudflare R2 instead of local MinIO

By default, local development uses RustFS, but it exercises the same S3/R2 code
paths as production. To point the stack at a **separate staging R2 account and
separate staging buckets**, copy `.env.local.example` to `.env.local`, fill in
the R2 values, and run:

```sh
docker compose --env-file .env.local -f docker-compose.local.yml up --build --remove-orphans
```

Never put production R2 credentials or production bucket names in a local
`.env.local`. The file is ignored by Git. `USE_R2_MEDIA=True` and
`BRIDGED_R2_PROBLEMS=True` are enabled by default so media and problem releases
follow the production storage path.

## Production

Production uses `docker-compose.production.yml` with the image built and
published by GitHub Actions. Production MariaDB, Redis, nginx, and judge
workers remain external to that compose file. See [CI-CD.md](CI-CD.md) for the
deployment workflow and [contributing.md](contributing.md) for code style.
