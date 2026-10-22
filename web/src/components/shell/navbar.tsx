"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { Code2, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { useUiStore } from "@/components/providers/ui-store-provider";

/*
 * Các trang OJ hiện vẫn do Django phục vụ (nginx định tuyến theo đường dẫn),
 * nên liên kết tới đó dùng <a> thường để tải đầy đủ trang, không dùng <Link>.
 */
const NAV_ITEMS = [
  { href: "/problems", label: "Đề bài" },
  { href: "/submissions/", label: "Bài nộp" },
  { href: "/contests/", label: "Cuộc thi" },
  { href: "/users/", label: "Xếp hạng" },
  { href: "/blogs/", label: "Blog" },
];

function isCurrent(pathname: string, href: string) {
  const base = href.replace(/\/$/, "");
  return pathname === base || pathname.startsWith(`${base}/`);
}

const navItemClass =
  "interactive focus-ring inline-flex items-center rounded-full border-2 border-transparent px-4 py-2 text-body font-extrabold text-foreground hover:bg-surface-muted motion-safe:hover:-translate-y-0.5";

export function Navbar() {
  const pathname = usePathname();
  const open = useUiStore((s) => s.mobileMenuOpen);
  const setOpen = useUiStore((s) => s.setMobileMenuOpen);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setOpen(false);
  }, [pathname, setOpen]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  return (
    <header className="sticky top-3 z-40 mx-auto w-full max-w-[1280px] px-4 pt-3">
      <nav
        aria-label="Điều hướng chính"
        className="relative flex items-center gap-3 rounded-full border-[3px] border-edge bg-surface px-4 py-2 shadow-hard-md"
      >
        <Link
          href="/"
          className="interactive focus-ring group/logo flex items-center gap-2 rounded-full pr-2 font-heading text-subheading font-extrabold text-foreground"
        >
          <span className="grid size-10 place-items-center rounded-xl border-[3px] border-edge bg-amber text-cocoa motion-safe:group-hover/logo:rotate-[8deg] motion-safe:group-hover/logo:scale-110 interactive">
            <Code2 aria-hidden="true" className="size-6" />
          </span>
          ThinkAlgo
        </Link>

        <ul className="ml-4 hidden flex-1 items-center gap-1 lg:flex">
          {NAV_ITEMS.map((item) => {
            const current = isCurrent(pathname, item.href);
            return (
              <li key={item.href}>
                <a
                  href={item.href}
                  aria-current={current ? "page" : undefined}
                  className={cn(
                    navItemClass,
                    current && "border-edge bg-amber text-cocoa hover:bg-amber",
                  )}
                >
                  {item.label}
                </a>
              </li>
            );
          })}
        </ul>

        <div className="ml-auto flex items-center gap-2 lg:ml-0">
          <ThemeToggle />
          <Button asChild size="sm" className="hidden sm:inline-flex">
            <a href="/login/">Đăng nhập</a>
          </Button>
          <Button
            ref={buttonRef}
            type="button"
            variant="secondary"
            size="icon"
            className="lg:hidden"
            aria-label={open ? "Đóng menu" : "Mở menu"}
            aria-expanded={open}
            aria-controls="mobile-menu"
            onClick={() => setOpen(!open)}
          >
            {open ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
          </Button>
        </div>

        {open && (
          <div
            id="mobile-menu"
            className="absolute inset-x-0 top-full mt-3 rounded-card border-[3px] border-edge bg-surface p-3 shadow-hard-lg lg:hidden"
          >
            <ul className="flex flex-col gap-1">
              {NAV_ITEMS.map((item) => {
                const current = isCurrent(pathname, item.href);
                return (
                  <li key={item.href}>
                    <a
                      href={item.href}
                      aria-current={current ? "page" : undefined}
                      className={cn(
                        navItemClass,
                        "w-full justify-start",
                        current && "border-edge bg-amber text-cocoa hover:bg-amber",
                      )}
                    >
                      {item.label}
                    </a>
                  </li>
                );
              })}
              <li className="pt-1 sm:hidden">
                <Button asChild className="w-full">
                  <a href="/login/">Đăng nhập</a>
                </Button>
              </li>
            </ul>
          </div>
        )}
      </nav>
    </header>
  );
}
