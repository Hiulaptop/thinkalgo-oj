#!/usr/bin/env bash
# Sinh snippet nginx `cloudflare-realip.conf` từ danh sách IP CHÍNH THỨC của Cloudflare.
#
# nginx chỉ tin header CF-Connecting-IP khi kết nối đến từ dải IP của Cloudflare
# (set_real_ip_from); nếu không, người dùng có thể giả IP. Danh sách thay đổi theo
# thời gian nên KHÔNG gõ tay vào repo: file này được sinh lúc deploy.
#
# Dùng:  scripts/gen_cloudflare_realip.sh <file-đầu-ra>
# Biến môi trường (tuỳ chọn, để kiểm thử/ghi đè): CF_IPS_V4_URL, CF_IPS_V6_URL.
# Thất bại (mã khác 0, không ghi file) nếu tải lỗi, rỗng hoặc có dòng không phải CIDR:
# không bao giờ sinh danh sách tin cậy rỗng/sai một cách im lặng.
set -euo pipefail

out="${1:?usage: gen_cloudflare_realip.sh <output-file>}"
v4_url="${CF_IPS_V4_URL:-https://www.cloudflare.com/ips-v4}"
v6_url="${CF_IPS_V6_URL:-https://www.cloudflare.com/ips-v6}"

tmp="$(mktemp)"
trap 'rm -f "$tmp" "$tmp.v4" "$tmp.v6"' EXIT

fetch() { curl -fsS --max-time 30 --retry 3 "$1"; }

fetch "$v4_url" | tr -d '\r' | sed '/^[[:space:]]*$/d' > "$tmp.v4"
fetch "$v6_url" | tr -d '\r' | sed '/^[[:space:]]*$/d' > "$tmp.v6"

cidr4='^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$'
cidr6='^[0-9A-Fa-f:]+/[0-9]{1,3}$'
for f in v4:"$cidr4" v6:"$cidr6"; do
  name="${f%%:*}"; re="${f#*:}"
  [ -s "$tmp.$name" ] || { echo "danh sách $name rỗng" >&2; exit 1; }
  if grep -Ev "$re" "$tmp.$name" | grep -q .; then
    echo "danh sách $name có dòng không phải CIDR:" >&2
    grep -Ev "$re" "$tmp.$name" >&2
    exit 1
  fi
done

{
  echo "# Sinh bởi scripts/gen_cloudflare_realip.sh từ danh sách IP chính thức của Cloudflare."
  echo "# KHÔNG sửa tay."
  cat "$tmp.v4" "$tmp.v6" | sed 's/^/set_real_ip_from /; s/$/;/'
  echo "real_ip_header CF-Connecting-IP;"
} > "$tmp"

mv "$tmp" "$out"
chmod 644 "$out"
echo "đã ghi $out ($(grep -c '^set_real_ip_from' "$out") dải IP)"
