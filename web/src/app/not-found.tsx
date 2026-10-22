import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "Không tìm thấy trang" };

export default function NotFound() {
  return (
    <section className="flex flex-col items-center gap-6 py-16 text-center">
      <svg
        aria-hidden="true"
        viewBox="0 0 160 120"
        className="h-40 w-52"
      >
        <circle cx="48" cy="64" r="34" fill="var(--color-amber)" stroke="var(--edge)" strokeWidth="5" />
        <rect x="84" y="30" width="56" height="56" rx="14" fill="var(--color-leaf)" stroke="var(--edge)" strokeWidth="5" />
        <path d="M30 98 L58 98 L44 74 Z" fill="var(--color-cyan)" stroke="var(--edge)" strokeWidth="5" strokeLinejoin="round" />
        <circle cx="38" cy="60" r="4" fill="var(--color-cocoa)" />
        <circle cx="58" cy="60" r="4" fill="var(--color-cocoa)" />
        <path d="M38 76 Q48 68 58 76" fill="none" stroke="var(--color-cocoa)" strokeWidth="4" strokeLinecap="round" />
      </svg>
      <p className="font-heading text-display font-extrabold">404</p>
      <h1 className="text-heading-sm">Ôi, lạc đường rồi!</h1>
      <p className="max-w-md text-body-lg">Trang bạn tìm không tồn tại hoặc đã được chuyển đi nơi khác.</p>
      <Button asChild>
        <Link href="/">Về trang chủ</Link>
      </Button>
    </section>
  );
}
