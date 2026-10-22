import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  [
    "interactive focus-ring inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap",
    "rounded-button border-2 border-edge font-extrabold",
    "disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-foreground/60 disabled:shadow-none",
    "aria-disabled:pointer-events-none aria-disabled:bg-surface-muted aria-disabled:text-foreground/60 aria-disabled:shadow-none",
    "motion-safe:active:translate-y-0.5 active:shadow-none",
    "[&_svg]:size-5 [&_svg]:shrink-0",
  ],
  {
    variants: {
      variant: {
        primary:
          "bg-amber text-cocoa shadow-hard-md hover:bg-orange hover:shadow-hard-lg motion-safe:hover:-translate-y-[3px] motion-safe:hover:scale-105",
        secondary:
          "bg-surface text-foreground shadow-hard-sm hover:bg-surface-muted hover:shadow-hard-md motion-safe:hover:-translate-y-[3px] motion-safe:hover:-rotate-1",
        ghost:
          "border-transparent bg-transparent text-foreground hover:border-edge hover:bg-surface-muted hover:shadow-hard-sm motion-safe:hover:-translate-y-0.5",
        danger:
          "bg-red text-white shadow-hard-md hover:shadow-hard-lg motion-safe:hover:-translate-y-[3px] motion-safe:hover:scale-105 hover:brightness-110",
      },
      size: {
        default: "px-6 py-3 text-body",
        sm: "px-4 py-2 text-caption",
        icon: "size-11 p-0",
      },
    },
    defaultVariants: { variant: "primary", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
