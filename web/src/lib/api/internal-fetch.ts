import http from "node:http";
import https from "node:https";

/**
 * `fetch` có thể đặt header `Host` (fetch của Node/undici bỏ qua `Host` do người gọi đặt và dùng
 * host của URL). Django kiểm tra ALLOWED_HOSTS nên cuộc gọi nội bộ tới 127.0.0.1:8000 phải mang
 * đúng Host của site (vd oj.thinkcode.vn), nếu không sẽ nhận 400 DisallowedHost. Đã gặp lỗi này
 * khi thử với Django thật.
 *
 * Triển khai tối giản bằng node:http, đủ cho openapi-fetch (không stream, không redirect).
 */
export async function internalFetch(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const body = request.method === "GET" || request.method === "HEAD" ? undefined : Buffer.from(await request.arrayBuffer());
  const headers: Record<string, string> = {};
  request.headers.forEach((value, key) => {
    headers[key] = value;
  });
  if (body) headers["content-length"] = String(body.length);

  const transport = url.protocol === "https:" ? https : http;
  return new Promise<Response>((resolve, reject) => {
    const req = transport.request(
      {
        protocol: url.protocol,
        hostname: url.hostname,
        port: url.port || undefined,
        path: url.pathname + url.search,
        method: request.method,
        headers,
        timeout: 15_000,
      },
      (res) => {
        const chunks: Buffer[] = [];
        res.on("data", (chunk: Buffer) => chunks.push(chunk));
        res.on("end", () => {
          const responseHeaders = new Headers();
          for (const [key, value] of Object.entries(res.headers)) {
            if (Array.isArray(value)) value.forEach((v) => responseHeaders.append(key, v));
            else if (value !== undefined) responseHeaders.set(key, value);
          }
          const status = res.statusCode ?? 502;
          const noBody = status === 204 || status === 304 || request.method === "HEAD";
          resolve(new Response(noBody ? null : Buffer.concat(chunks), { status, headers: responseHeaders }));
        });
      },
    );
    req.on("timeout", () => req.destroy(new Error("Hết thời gian chờ Django")));
    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}
