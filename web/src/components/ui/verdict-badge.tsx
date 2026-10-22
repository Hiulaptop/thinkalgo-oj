import type { ComponentType, SVGProps } from "react";
import { Check, Clock, FileWarning, LoaderCircle, MemoryStick, TriangleAlert, X, Bug, CircleDashed } from "lucide-react";
import { cn } from "@/lib/utils";

type IconType = ComponentType<SVGProps<SVGSVGElement> & { size?: number | string }>;

interface VerdictStyle {
  label: string;
  title: string;
  icon: IconType;
  className: string;
  spin?: boolean;
}

/*
 * Trạng thái chấm bài theo style.md. Màu luôn đi kèm icon và nhãn chữ.
 * RE/IR dùng nền Cocoa chữ Cream (Copper + chữ trắng chỉ đạt 3.6:1, không đủ AA).
 */
const VERDICTS: Record<string, VerdictStyle> = {
  AC: { label: "AC", title: "Chấp nhận: đúng trên mọi test", icon: Check, className: "bg-leaf text-cocoa" },
  WA: { label: "WA", title: "Sai đáp án", icon: X, className: "bg-red text-white" },
  TLE: { label: "TLE", title: "Quá thời gian cho phép", icon: Clock, className: "bg-orange text-cocoa" },
  MLE: { label: "MLE", title: "Quá giới hạn bộ nhớ", icon: MemoryStick, className: "bg-orange text-cocoa" },
  OLE: { label: "OLE", title: "Quá giới hạn dữ liệu xuất", icon: FileWarning, className: "bg-orange text-cocoa" },
  RE: { label: "RE", title: "Lỗi khi chạy chương trình", icon: TriangleAlert, className: "bg-cocoa text-cream [&_svg]:text-amber" },
  IR: { label: "IR", title: "Chương trình thoát bất thường", icon: TriangleAlert, className: "bg-cocoa text-cream [&_svg]:text-amber" },
  CE: { label: "CE", title: "Lỗi biên dịch", icon: Bug, className: "bg-sand text-cocoa" },
  PARTIAL: {
    label: "Một phần",
    title: "Đúng một phần số test",
    icon: CircleDashed,
    className: "border-[3px] border-leaf bg-sand text-cocoa",
  },
  PENDING: { label: "Đang chấm", title: "Bài nộp đang được chấm", icon: LoaderCircle, className: "bg-amber text-cocoa", spin: true },
};

const ALIASES: Record<string, string> = {
  RTE: "RE",
  P: "PARTIAL",
  QU: "PENDING",
  G: "PENDING",
  GRADING: "PENDING",
  QUEUED: "PENDING",
};

export function normalizeVerdict(status: string): string {
  const key = status.trim().toUpperCase();
  return ALIASES[key] ?? key;
}

export function VerdictBadge({ status, className }: { status: string; className?: string }) {
  const key = normalizeVerdict(status);
  const known = VERDICTS[key];
  const style: VerdictStyle = known ?? {
    label: status,
    title: `Trạng thái: ${status}`,
    icon: CircleDashed,
    className: "bg-sand text-cocoa",
  };
  const Icon = style.icon;
  return (
    <span
      title={style.title}
      className={cn(
        "interactive inline-flex cursor-help items-center gap-1.5 rounded-full border-2 border-edge px-3 py-0.5 text-caption font-extrabold whitespace-nowrap",
        "motion-safe:hover:scale-110 motion-safe:hover:rotate-3",
        style.className,
        className,
      )}
    >
      <Icon aria-hidden="true" size={16} className={cn(style.spin && "motion-safe:animate-spin")} />
      {style.label}
    </span>
  );
}
