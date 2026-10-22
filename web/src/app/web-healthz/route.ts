// Kiểm tra sống cho Docker/CD, nginx chỉ cho phép gọi từ 127.0.0.1.
// Không đặt dưới thư mục bắt đầu bằng "_" (App Router coi đó là private).
export const dynamic = "force-dynamic";

export function GET() {
  return new Response("ok", { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
