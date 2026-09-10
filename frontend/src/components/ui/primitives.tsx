import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/* ---------------------------------------------------------------- Button */
type BtnVariant = "primary" | "ghost" | "outline" | "danger" | "subtle";
export function Button({
  className,
  variant = "outline",
  size = "md",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant; size?: "sm" | "md" | "lg" }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40 disabled:active:scale-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/80 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
        size === "sm" && "h-8 px-3 text-xs",
        size === "md" && "h-9 px-4 text-sm",
        size === "lg" && "h-11 px-6 text-sm",
        variant === "primary" && "bg-white text-black hover:bg-zinc-200",
        variant === "outline" && "border border-white/10 bg-transparent text-white hover:border-white/20 hover:bg-white/[0.05]",
        variant === "ghost" && "text-muted hover:bg-white/[0.06] hover:text-white",
        variant === "subtle" && "bg-white/[0.07] text-white hover:bg-white/[0.11]",
        variant === "danger" && "bg-critical text-white hover:opacity-90",
        className,
      )}
      {...props}
    />
  );
}

/* ---------------------------------------------------------------- Card */
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-lg border border-white/[0.09] bg-[#090909] shadow-card", className)}
      {...props}
    />
  );
}
export function CardHeader({
  title,
  subtitle,
  actions,
  className,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-4 border-b border-white/[0.08] px-5 py-4", className)}>
      <div>
        <h3 className="text-[13px] font-semibold tracking-[-0.01em] text-zinc-100">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

/* ---------------------------------------------------------------- Badge */
export function Badge({
  className,
  tone = "neutral",
  ...props
}: HTMLAttributes<HTMLSpanElement> & {
  tone?: "neutral" | "accent" | "critical" | "high" | "medium" | "low" | "success";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-2xs font-medium ring-1 ring-inset",
        tone === "neutral" && "bg-white/[0.05] text-zinc-300 ring-white/10",
        tone === "accent" && "bg-white text-black ring-white",
        tone === "critical" && "bg-critical/15 text-critical ring-critical/30",
        tone === "high" && "bg-high/15 text-high ring-high/30",
        tone === "medium" && "bg-medium/15 text-medium ring-medium/30",
        tone === "low" && "bg-low/15 text-low ring-low/30",
        tone === "success" && "bg-low/15 text-low ring-low/30",
        className,
      )}
      {...props}
    />
  );
}

/* ---------------------------------------------------------------- Input / Select */
export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-lg border border-white/10 bg-black px-3 text-sm text-white transition-colors duration-200 placeholder:text-zinc-600 hover:border-white/20 focus-visible:border-white/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-10 w-full rounded-lg border border-white/10 bg-black px-3 text-sm text-white transition-colors duration-200 hover:border-white/20 focus-visible:border-white/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

/* ---------------------------------------------------------------- Progress */
export function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-white/10", className)}>
      <div
        className="h-full rounded-full bg-white transition-all duration-300"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

/* ---------------------------------------------------------------- Skeleton / Empty */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton rounded-md", className)} />;
}
export function EmptyState({
  icon,
  title,
  hint,
  action,
}: {
  icon?: ReactNode;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      {icon && <div className="mb-1 text-zinc-600">{icon}</div>}
      <p className="text-sm font-medium text-white">{title}</p>
      {hint && <p className="max-w-sm text-xs leading-5 text-muted">{hint}</p>}
      {action}
    </div>
  );
}

/* ---------------------------------------------------------------- Stat number */
export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div>
      <div className="text-2xs font-medium uppercase tracking-[0.12em] text-muted">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
      {hint && <div className="mt-0.5 text-2xs text-muted">{hint}</div>}
    </div>
  );
}
