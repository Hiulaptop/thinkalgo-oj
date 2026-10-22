import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Image production tối giản: server.js + các phụ thuộc đã được theo dõi.
  output: "standalone",
  // Gốc repo có package.json của Django/websocket; ghim gốc theo dõi vào web/ để
  // server.js luôn nằm ở gốc thư mục standalone dù build ở đâu.
  outputFileTracingRoot: path.join(__dirname),
  // nginx đã nén (gzip); không nén thêm ở Node.
  compress: false,
  poweredByHeader: false,
  // Django: danh sách có "/" cuối (/problems/), chi tiết không (/problem/<mã>); tự 301 giữa hai dạng.
  // Next.js không được tự đổi dấu "/" kẻo vòng lặp chuyển hướng với APPEND_SLASH
  // của Django; nginx chỉ gửi đúng URL chuẩn của từng route tới đây.
  skipTrailingSlashRedirect: true,
  async headers() {
    return [
      {
        // Trang tĩnh của Next.js mặc định gửi `s-maxage=31536000`, CDN có thể giữ
        // HTML cũ cả năm. /_next/static (tên có hash) vẫn giữ `immutable` mặc định.
        source: "/((?!_next/static|_next/image).*)",
        headers: [{ key: "Cache-Control", value: "private, no-cache" }],
      },
    ];
  },
};

export default nextConfig;
