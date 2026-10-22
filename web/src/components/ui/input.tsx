import * as React from "react";
import { cn } from "@/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "interactive focus-ring w-full rounded-input border-2 border-edge bg-surface px-3.5 py-2.5 text-body text-foreground",
        "placeholder:text-foreground/70 hover:bg-surface-muted hover:shadow-hard-sm",
        "disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-foreground/60 disabled:shadow-none",
        "aria-invalid:border-[3px] aria-invalid:border-red [[data-theme=dark]_&]:aria-invalid:border-orange",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export { Input };
