import type { ButtonHTMLAttributes } from "react";

type Variant = "default" | "primary" | "secondary" | "ghost" | "outline";
type Size = "default" | "sm" | "lg";

const VARIANTS: Record<Variant, string> = {
  default: "bg-accent text-accent-fg hover:bg-accent/90",
  primary: "bg-accent text-accent-fg hover:bg-accent/90",
  outline: "border border-border text-fg hover:border-accent/50",
  secondary: "border border-border bg-surface-2 text-fg hover:border-accent/50",
  ghost: "text-muted hover:text-fg",
};

export function Button({
  variant = "primary",
  size = "default",
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return (
    <button
      type={type}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-md ${size === "lg" ? "px-6 text-sm" : "px-4 text-xs"} font-mono tracking-widest transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}
