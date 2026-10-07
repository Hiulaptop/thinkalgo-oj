// websocket/config.js template for the Dockerized deployment.
//
// websocket/config.js itself is gitignored (see .gitignore) because in the
// native deployment it's generated per-server by vnoi_setup.sh alongside
// dmoj/local_settings.py. For the Docker image, these values are static
// (they're internal container ports, not secrets, and don't vary between
// environments the way DB/SMTP credentials do), so this checked-in template
// is copied to websocket/config.js at image build time (see Dockerfile).
//
// Matches thinkcode-deploy/docker-compose.production.yml's wsevent service
// (network_mode: host, ports 15100/15101/15102) and nginx/vnoj.conf.docker's
// /event/ and /channels/ proxy_pass targets.
//
// Bind hosts/ports are overridable via WSEVENT_{GET,POST,HTTP}_BIND_{HOST,PORT}
// env vars, defaulting to the production values above so an unset env (as in
// production, which only sets DJANGO_SETTINGS_MODULE) is a no-op. Deliberately
// a *different* name than Django's WSEVENT_POST_HOST (local_settings.docker.py.example,
// EVENT_DAEMON_POST) and docker-compose.dev.yml's WSEVENT_DJANGO_CONNECT_HOST
// -- those tell Django/other containers which *hostname* to dial (e.g.
// `wsevent`, resolved over the Docker network), which is a different value
// than what this process should *bind* to (`0.0.0.0`). Reusing one name for
// both would make the wsevent container try to bind its own service name.
//
// This matters for docker-compose.local.yml, which runs on a bridge network
// (not network_mode: host like production): binding 127.0.0.1 here is only
// reachable from inside this exact container, so `site`/`bridged`/`celery`
// posting events to the `wsevent` service name over the Docker network would
// silently fail without a 0.0.0.0 bind.
const config = {
  get_host: process.env.WSEVENT_GET_BIND_HOST || '127.0.0.1',
  get_port: Number(process.env.WSEVENT_GET_BIND_PORT) || 15100,
  post_host: process.env.WSEVENT_POST_BIND_HOST || '127.0.0.1',
  post_port: Number(process.env.WSEVENT_POST_BIND_PORT) || 15101,
  http_host: process.env.WSEVENT_HTTP_BIND_HOST || '127.0.0.1',
  http_port: Number(process.env.WSEVENT_HTTP_BIND_PORT) || 15102,
  long_poll_timeout: 29000,
};

export default config;
