import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { serverApi } from "@/lib/api/client";

export const metadata: Metadata = { title: "Thử API", robots: { index: false } };
export const dynamic = "force-dynamic";

// Trang nội bộ để kiểm tra Next.js gọi được Django và chuyển tiếp đúng cookie/header.
// Chỉ có ở môi trường phát triển.
export default async function ApiProbePage() {
  if (process.env.NODE_ENV === "production") notFound();

  const api = await serverApi();
  const [me, problems] = await Promise.all([
    api.GET("/api/v1/me"),
    api.GET("/api/v1/problems", { params: { query: { page_size: 3 } } }),
  ]);

  return (
    <>
      <h1 className="mb-6 text-heading">Thử API</h1>
      <h2 className="mb-2 text-subheading">GET /api/v1/me</h2>
      <pre data-testid="me" className="mb-8 overflow-x-auto rounded-card border-[3px] border-edge bg-surface-muted p-4 text-caption">
        {JSON.stringify({ status: me.response.status, data: me.data, error: me.error }, null, 2)}
      </pre>
      <h2 className="mb-2 text-subheading">GET /api/v1/problems?page_size=3</h2>
      <pre data-testid="problems" className="overflow-x-auto rounded-card border-[3px] border-edge bg-surface-muted p-4 text-caption">
        {JSON.stringify(
          { status: problems.response.status, codes: problems.data?.results.map((p) => p.code), has_next: problems.data?.has_next },
          null,
          2,
        )}
      </pre>
    </>
  );
}
