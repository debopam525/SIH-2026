import { createContext, useCallback, useContext, useState } from "react";
import type { ReactNode } from "react";
import { CheckCircle2, Info, TriangleAlert, X } from "lucide-react";
import { cn } from "@/lib/utils";

type Kind = "success" | "error" | "info";
interface Toast {
  id: number;
  kind: Kind;
  title: string;
  body?: string;
}

const Ctx = createContext<(t: Omit<Toast, "id">) => void>(() => {});
export const useToast = () => useContext(Ctx);

let seq = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = seq++;
    setToasts((x) => [...x, { ...t, id }]);
    setTimeout(() => setToasts((x) => x.filter((y) => y.id !== id)), 5000);
  }, []);

  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-4 bottom-4 z-[100] flex flex-col gap-2 sm:left-auto sm:w-80">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cn(
              "toast-enter pointer-events-auto flex items-start gap-2.5 rounded-lg border bg-[#111] p-3.5 shadow-pop",
              t.kind === "success" && "border-low/40",
              t.kind === "error" && "border-critical/40",
              t.kind === "info" && "border-border",
            )}
          >
            {t.kind === "success" && <CheckCircle2 size={16} className="mt-0.5 text-low" />}
            {t.kind === "error" && <TriangleAlert size={16} className="mt-0.5 text-critical" />}
            {t.kind === "info" && <Info size={16} className="mt-0.5 text-accent" />}
            <div className="flex-1">
              <p className="text-xs font-semibold">{t.title}</p>
              {t.body && <p className="mt-0.5 text-2xs text-muted">{t.body}</p>}
            </div>
            <button
              onClick={() => setToasts((x) => x.filter((y) => y.id !== t.id))}
              aria-label="Dismiss notification"
              className="text-muted hover:text-text"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
