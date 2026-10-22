#!/usr/bin/env bash
# Áp dụng cấu hình nginx từ một thư mục "staging" lên server, an toàn và hoàn tác được.
# Chạy TRÊN SERVER (CD gọi qua SSH). Không bao giờ để nginx đang chạy mất cấu hình tốt:
#   1. đặt cấu hình mới cạnh cấu hình cũ, hoán đổi bằng đổi tên thư mục;
#   2. `nginx -t`; lỗi thì trả cấu hình cũ, thoát mã khác 0, KHÔNG reload;
#   3. reload, rồi kiểm tra site còn trả lời; lỗi thì trả cấu hình cũ và reload lại.
#
# Dùng:  deploy_nginx_config.sh <thư-mục-staging>
# Biến môi trường (có mặc định cho production):
#   NGINX_DIR          thư mục cấu hình đang dùng   (/var/www/thinkcodeoj/nginx)
#   NGINX_TEST_CMD     lệnh kiểm tra cú pháp        (sudo -n nginx -t)
#   NGINX_RELOAD_CMD   lệnh reload                  (sudo -n systemctl reload nginx)
#   NGINX_VERIFY_URL   URL kiểm tra sau reload      (http://127.0.0.1/)
#   NGINX_VERIFY_HOST  header Host khi kiểm tra     (oj.thinkcode.vn)
#   NGINX_KEEP_BACKUPS số bản sao lưu giữ lại       (3)
set -euo pipefail

staging="${1:?usage: deploy_nginx_config.sh <staging-dir>}"
dir="${NGINX_DIR:-/var/www/thinkcodeoj/nginx}"
test_cmd="${NGINX_TEST_CMD:-sudo -n nginx -t}"
reload_cmd="${NGINX_RELOAD_CMD:-sudo -n systemctl reload nginx}"
verify_url="${NGINX_VERIFY_URL:-http://127.0.0.1/}"
verify_host="${NGINX_VERIFY_HOST:-oj.thinkcode.vn}"
keep="${NGINX_KEEP_BACKUPS:-3}"

[ -f "$staging/oj.conf" ] || { echo "staging thiếu oj.conf: $staging" >&2; exit 2; }
[ -f "$staging/snippets/cloudflare-realip.conf" ] || { echo "staging thiếu snippets/cloudflare-realip.conf (chạy scripts/gen_cloudflare_realip.sh)" >&2; exit 2; }

# Hậu tố duy nhất (kể cả hai lần chạy trong cùng một giây) để không bao giờ ghi đè
# hay lồng vào bản sao lưu đã có.
stamp="$(date +%Y%m%d%H%M%S).$$"
new="$dir.new"
prev="$dir.prev.$stamp"
[ ! -e "$prev" ] || { echo "bản sao lưu đã tồn tại: $prev" >&2; exit 2; }

rm -rf "$new"
cp -a "$staging" "$new"

swapped=0
if [ -d "$dir" ]; then
  mv "$dir" "$prev"
  swapped=1
fi
mv "$new" "$dir"

rollback() {
  echo "hoàn tác về cấu hình trước" >&2
  rm -rf "$dir"
  if [ "$swapped" = 1 ]; then mv "$prev" "$dir"; fi
}

if ! $test_cmd; then
  echo "nginx -t thất bại, giữ nguyên cấu hình cũ" >&2
  rollback
  exit 1
fi

$reload_cmd

# `reload` là bất đồng bộ: ngay sau đó request vẫn có thể rơi vào worker cũ (cấu hình
# cũ, còn trả lời tốt). Chờ rồi kiểm tra liên tiếp; MỌI lần kiểm tra phải đạt, nếu
# không coi như hỏng và hoàn tác.
sleep 2
ok=1
code=000
for _ in 1 2 3 4 5; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' -m 10 -H "Host: $verify_host" "$verify_url" || true)"
  case "$code" in 2??|3??) ;; *) ok=0; break ;; esac
  sleep 1
done
if [ "$ok" != 1 ]; then
  echo "kiểm tra sau reload thất bại (HTTP $code), hoàn tác" >&2
  rollback
  $reload_cmd || true
  exit 1
fi

# Dọn bản sao lưu cũ, giữ $keep bản mới nhất.
ls -1dt "$dir".prev.* 2>/dev/null | tail -n +"$((keep + 1))" | xargs -r rm -rf
echo "đã áp dụng cấu hình nginx ($stamp); bản trước: $prev"
