import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-5 border-b border-white/[0.08] px-4 py-7 sm:px-6 lg:flex-row lg:items-end lg:justify-between lg:px-8 lg:py-9">
      <div className="min-w-0">
        <div className="mb-3 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.16em] text-zinc-600">
          <span>Workspace</span><span className="text-zinc-800">/</span><span className="text-zinc-500">{title}</span>
        </div>
        <h1 className="text-2xl font-semibold tracking-[-0.04em] text-white sm:text-[30px]">{title}</h1>
        {description && <p className="mt-2 max-w-3xl text-xs leading-5 text-zinc-500 sm:text-[13px]">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}
