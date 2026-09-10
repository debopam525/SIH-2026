import { useEffect } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  children,
  width = "max-w-2xl",
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  width?: string;
}) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    if (open) window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);

  return (
    <div className={cn("fixed inset-0 z-50", !open && "pointer-events-none")}>
      <div
        className={cn(
          "absolute inset-0 bg-black/75 backdrop-blur-sm transition-opacity duration-200",
          open ? "opacity-100" : "opacity-0",
        )}
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          "absolute right-0 top-0 flex h-full w-full flex-col border-l border-white/10 bg-[#0a0a0a] shadow-pop transition-transform duration-200",
          width,
          open ? "translate-x-0 ease-out" : "translate-x-full ease-in",
        )}
      >
        <div className="flex items-start justify-between gap-3 border-b border-white/10 px-5 py-5 sm:px-6">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold tracking-tight">{title}</h2>
            {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
          </div>
          <button aria-label="Close dialog" onClick={onClose} className="rounded-md p-1.5 text-muted hover:bg-white/[0.06] hover:text-text">
            <X size={16} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">{children}</div>
      </div>
    </div>
  );
}
