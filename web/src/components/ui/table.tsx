import * as React from "react";
import { cn } from "@/lib/utils";

const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <div className="w-full overflow-x-auto rounded-card border-[3px] border-edge bg-surface">
      <table ref={ref} className={cn("w-full caption-bottom text-caption", className)} {...props} />
    </div>
  ),
);
Table.displayName = "Table";

const TableHeader = ({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => (
  <thead
    className={cn(
      "border-b-[3px] border-edge text-cocoa",
      // Hàng tiêu đề luôn nền Amber (chữ Cocoa), không đổi khi hover hay xen kẽ.
      "[&>tr]:bg-amber [&>tr]:even:bg-amber [&>tr]:hover:bg-amber [&>tr:hover>td:first-child]:shadow-none",
      className,
    )}
    {...props}
  />
);

const TableBody = ({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => (
  <tbody className={cn(className)} {...props} />
);

/*
 * Hàng bảng: hover đổi nền + thanh nhấn Amber bên trái. Không animate bóng
 * từng hàng để bảng dài vẫn mượt.
 */
const TableRow = ({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) => (
  <tr
    className={cn(
      "group/row border-b-2 border-edge/15 bg-surface transition-colors duration-150 even:bg-surface-muted",
      "hover:bg-row-hover hover:[&>td:first-child]:shadow-[inset_6px_0_0_0_var(--color-amber)]",
      className,
    )}
    {...props}
  />
);

const TableHead = ({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
  <th scope="col" className={cn("px-4 py-2.5 text-left font-extrabold", className)} {...props} />
);

const TableCell = ({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
  <td className={cn("px-4 py-2.5 align-middle", className)} {...props} />
);

export { Table, TableHeader, TableBody, TableRow, TableHead, TableCell };
