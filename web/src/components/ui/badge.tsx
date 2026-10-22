import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border-2 border-edge px-3 py-0.5 text-micro font-extrabold whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "bg-surface-muted text-foreground",
        amber: "bg-amber text-cocoa",
        orange: "bg-orange text-cocoa",
        leaf: "bg-leaf text-cocoa",
        cyan: "bg-cyan text-cocoa",
        red: "bg-red text-white",
        dark: "bg-cocoa text-cream",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
