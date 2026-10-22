import * as React from "react";
import { cn } from "@/lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Card bấm được: nâng lên, nghiêng nhẹ và tăng bóng đổ khi hover. */
  interactive?: boolean;
  tone?: "default" | "muted";
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, interactive = false, tone = "default", ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-card border-[3px] border-edge p-6 text-foreground shadow-hard-md",
        tone === "default" ? "bg-surface" : "bg-surface-muted",
        interactive &&
          "interactive focus-ring group/card cursor-pointer hover:border-copper hover:shadow-hard-xl motion-safe:hover:-translate-y-1.5 motion-safe:hover:-rotate-[0.5deg] motion-safe:active:translate-y-0.5 active:shadow-hard-sm",
        className,
      )}
      {...props}
    />
  ),
);
Card.displayName = "Card";

const CardTitle = ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={cn("font-heading text-subheading font-bold", className)} {...props} />
);

const CardDescription = ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
  <p className={cn("mt-2 text-body text-foreground", className)} {...props} />
);

export { Card, CardTitle, CardDescription };
