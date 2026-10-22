import createClient from "openapi-fetch";
import { headers as incomingHeaders } from "next/headers";
import { internalFetch } from "./internal-fetch";
import type { paths } from "./schema";

/**
 * Máy khách API Django dùng ở phía server (Server Component, route handler).
 *
 * Trình duyệt không gọi trực tiếp /api/v1; Next.js gọi Django qua địa chỉ nội bộ và chuyển tiếp
 * những thứ Django cần để nhận đúng người dùng:
 *   - Cookie (session), để áp dụng đúng quyền của người xem;
 *   - X-Real-IP / X-Forwarded-Proto do nginx đặt (IP thật, HTTPS gốc);
 *   - Accept-Language, X-Request-Id.
 * Django bật `TRUSTED_PROXY_IPS` để tin X-Real-IP khi kết nối đến từ loopback.
 */
const DJANGO_INTERNAL_URL = process.env.DJANGO_INTERNAL_URL ?? "http://127.0.0.1:8000";
// ALLOWED_HOSTS của Django chỉ có tên miền site nên phải gửi đúng Host.
const DJANGO_HOST = process.env.DJANGO_HOST;

const FORWARDED = ["cookie", "x-real-ip", "x-forwarded-proto", "accept-language", "x-request-id"] as const;

export async function serverApi() {
  const incoming = await incomingHeaders();
  const headers: Record<string, string> = {};
  for (const name of FORWARDED) {
    const value = incoming.get(name);
    if (value) headers[name] = value;
  }
  if (DJANGO_HOST) headers["host"] = DJANGO_HOST;

  return createClient<paths>({
    baseUrl: DJANGO_INTERNAL_URL,
    headers,
    // node:http để đặt được header Host (fetch của Node bỏ qua); luôn lấy mới vì dữ liệu phụ thuộc người xem.
    fetch: internalFetch,
  });
}
