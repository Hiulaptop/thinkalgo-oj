# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ThinkAlgo OJ (repo: `thinkalgo-oj`) — a fork of [VNOJ](https://github.com/VNOI-Admin/OJ) / [DMOJ](https://github.com/DMOJ/online-judge), a competitive-programming online judge. Live at `oj.thinkcode.vn`. Native install follows the [VNOJ docs](https://vnoi-admin.github.io/vnoj-docs/#/site/installation); production is Docker-only.

## Mandatory working rules

- **Default to superpowers.** Use the project's skill set (brainstorming, systematic-debugging, writing-plans, etc.) as the default way of working in this repo, not as an opt-in.
- **Any UI change goes through `style.md` first.** Before touching templates, SCSS/CSS, or component markup, read `style.md` in the repo root and follow its tokens, components, and do's/don'ts. This is the authoritative design-system reference — don't invent colors, spacing, or type choices outside it.

## Commands

### Tests
```bash
# Full suite (same as CI) — needs dmoj/local_settings.py in place (see Local dev below)
python manage.py test judge urlshortener

# Single test module / class / method
python manage.py test judge.tests.test_problem_releases
python manage.py test judge.tests.test_problem_releases.BuildReleaseTest
python manage.py test judge.tests.test_problem_releases.BuildReleaseTest.test_build_release_deterministic_hash

# With coverage (as CI does)
coverage run --source=. manage.py test judge urlshortener
```

### Lint
```bash
flake8                      # max-line-length 120, pycharm import order, see .flake8 for per-file ignores
python -m compileall -q .   # syntax check
```

### Styles / JS
```bash
./make_style.sh             # builds SCSS -> CSS (requires npm ci first)
npm run format               # prettier --write websocket
npm run format:check         # prettier --check websocket
```

### Django management
```bash
python manage.py migrate
python manage.py check
python manage.py check --deploy --fail-level ERROR
python manage.py collectstatic --noinput
python manage.py compilemessages
python manage.py compilejsi18n
```

### Local dev (Docker, fastest path)
```bash
docker compose -f docker-compose.dev.yml up --build -d
# first run only, once `db` is healthy:
docker compose -f docker-compose.dev.yml exec site python3 manage.py migrate
docker compose -f docker-compose.dev.yml exec site python3 manage.py createsuperuser
docker compose -f docker-compose.dev.yml exec site python3 manage.py loaddata judge/fixtures/navbar.json judge/fixtures/language_small.json
# or, for a fuller sample dataset:
docker compose -f docker-compose.dev.yml exec site python3 manage.py loaddata demo
```
Site: `http://localhost:8000/`. Source is baked into the image, not bind-mounted — code changes need `up --build` again, no hot reload.

The compose file also defines `minio`/`minio-init` (local S3-compatible stand-in for R2, used by Polygon import). Both `quay.io/minio/mc` and Docker Hub's `minio/minio` have been observed returning 401/access-denied for anonymous pulls — if that happens, start without them (`up --build -d db redis site bridged celery wsevent nginx`); nothing else depends on them unless you're testing Polygon import.

**Windows checkout gotcha:** if `make_style.sh` (or any other repo shell script) fails in a Docker build with `not found` / exit 127, check for CRLF line endings introduced by `core.autocrlf=true` corrupting the shebang line. Fix locally with `sed -i 's/\r$//' <file>` — the committed blob is already LF per `.gitattributes`, so this is a local-checkout fix, not a code change (verify with `git diff` showing nothing).

### Local dev (non-Docker)
`cp .ci.settings.py dmoj/local_settings.py` gives a secrets-free settings file (SQLite) good enough for `collectstatic`/`compilemessages`/`compilejsi18n`/tests, matching what CI uses — but production uses MariaDB/MySQL, not SQLite.

## Architecture

### It's two Django apps and four runtime processes, one Docker image

`judge` is the main app; `urlshortener` is a small second app. Both get run through `manage.py test judge urlshortener`. First-party/vendored Django apps living at the repo root: `django_ace`, `martor` (markdown editor fork).

One Docker image (built from the root `Dockerfile`) runs as four different services depending on the container command — see `docker-compose.production.yml` / `docker-compose.dev.yml`:
- **site** — `uwsgi --module dmoj.wsgi:application` (the Django app itself)
- **bridged** — `python3 manage.py runbridged`: the site's half of the site↔judge dispatch protocol (`judge/bridge/`). **This is not the sandboxed code-execution judge** — that lives in a separate repo (`thinkcode-judge-server`, see README). `bridged` only decides what to dispatch and talks to judges over a socket protocol (`judge_handler.py`).
- **celery** — `celery -A dmoj_celery worker`, using the top-level `dmoj_celery.py` shim (the actual Celery app object is `dmoj.celery.app`, name `'dmoj'`).
- **wsevent** — `node websocket/daemon.js`, a separate Node.js process for live submission/contest updates over WebSocket. Config is `websocket/config.js`, gitignored and generated per-environment (`websocket/config.docker.js` is the checked-in Docker template, copied in at build time).

### Settings layering: base → `local_settings.py` via `exec()`

`dmoj/settings.py` ends with:
```python
try:
    with open(os.path.join(os.path.dirname(__file__), 'local_settings.py')) as f:
        exec(f.read(), globals())
except IOError:
    pass
```
`local_settings.py` is `exec()`'d directly into `settings.py`'s own globals (not imported as a module) — it can read and override any name already defined above it in `settings.py`, and the order of assignments matters. `dmoj/local_settings.py` is gitignored.

Three different "local settings" exist for three different contexts — don't confuse them:
- **`.ci.settings.py`** — checked in, no secrets, SQLite-backed. Used by CI and by the site image's own build step (`RUN cp .ci.settings.py dmoj/local_settings.py && ./make_style.sh && collectstatic ...`) to produce static assets without a real DB.
- **`dmoj/local_settings.docker.py.example`** — checked in, no secrets, reads everything from environment variables. This is **not just a template**: `Dockerfile` does `COPY dmoj/local_settings.docker.py.example dmoj/local_settings.py` to produce the actual production settings file baked into the runtime image. Any production settings change goes here.
- **`dmoj/local_settings.py`** (real, gitignored) — what you'd hand-write for a native/non-Docker install.

### Templates: Jinja2 for the app, Django templates for admin

`TEMPLATES` in `settings.py` configures `django_jinja.backend.Jinja2` (`APP_DIRS: False`, explicit dirs) for the main `templates/` tree, plus a second standard Django-templates backend (`APP_DIRS: True`) for apps like `django.contrib.admin` that ship their own templates. Jinja2 templates use `{{ static(...) }}` (a custom global, not Django's `{% static %}` tag) to resolve static URLs.

### Static assets: django-compressor runs in online mode

`COMPRESS_OFFLINE` is not set, so compressor computes CSS/JS bundle hashes and writes them to `STATIC_ROOT/cache/{css,js}/` **at request time**, inside whichever container serves the request — it is not a fixed, pre-baked artifact from image build time. In production this means the compressor cache directory must be the *same* directory nginx reads static files from (a bind-mount, not a one-time `docker cp`), or you get 404s on `/static/cache/css/output.<hash>.css` after a deploy. See `CI-CD.md` §3.4 for the full incident writeup if touching the static-serving path. `COMPRESS_OFFLINE=True` was considered and rejected because `{% compress css %}` in `templates/base.html` branches on the user's theme/cookie, so there's no single correct offline-compiled output.

### R2 (Cloudflare) is three unrelated subsystems — don't conflate them

1. **Media storage** (`USE_R2_MEDIA`) — avatars/Martor-uploaded images/PDF statements/admin static-uploads via `django-storages` `S3Storage`, custom domain `media.oj.thinkcode.vn`. Submission source files and contest replay data are deliberately kept off this path (served through Django for access control, not as public CDN-cacheable URLs).
2. **Problem test-data releases** (`BRIDGED_R2_PROBLEMS`) — `judge/utils/problem_releases.py` publishes immutable, sha256-verified, versioned zip packages of a problem's local test data to R2 whenever test data is saved in the admin UI (`judge/views/problem_data.py` → `judge/tasks/problem.py:publish_problem_release`), and purges them on problem delete (`judge/signals.py`, deferred via `transaction.on_commit`). Judges download and grade from these packages instead of a shared local directory. Ops CLI: `manage.py publish_problem_release CODE [VERSION]` and `manage.py r2_problem_release {list,show,delete,purge} CODE [VERSION]`.
3. **MariaDB backups** — separate credential, `deploy/thinkcode-r2-backup.service`/`.timer` + `scripts/backup_mariadb_to_r2.sh`.

Full deploy/runtime details (GitHub Actions secrets, Cloudflare cache rules, rollback procedure) are in `CI-CD.md`, not duplicated here.

### Judge app internal layout

- `judge/models/` — DB models
- `judge/views/` — request handlers
- `judge/bridge/` — site↔judge dispatch protocol (`judge_handler.py`)
- `judge/tasks/` — Celery tasks
- `judge/utils/` — shared utilities (incl. `problem_releases.py`)
- `judge/contest_format/` — pluggable contest scoring/ranking formats
- `judge/balancer/` — judge load-balancing (`runbalancer.py`)
- `judge/jinja2/` — Jinja2 environment globals/filters (e.g. `gravatar`)
- `judge/templatetags/`, `judge/widgets/`, `judge/admin/` — as named
- `judge/management/commands/` — many one-off ops scripts (user/problem backfills, Polygon import, PDF rendering, etc.) in addition to the long-running `runbridged`/`runbalancer`

## Coding conventions

- flake8-enforced: max line length 120, `pycharm` import-order style, `application-import-names = dmoj,judge,urlshortener,django_ace,martor`. See `.flake8` for per-file exceptions (migrations exempt from line length, `__init__.py` exempt from unused-import rules).
- Vietnamese translations live in `locale/vi/LC_MESSAGES`.
