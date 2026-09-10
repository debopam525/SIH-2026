import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard, ScanLine, Boxes, AppWindow, ArrowRightLeft,
  KanbanSquare, FileText, Settings2, LogOut, ShieldHalf, Menu, X,
} from "lucide-react";
import { useAuth } from "@/store/auth";
import { ScanPicker } from "@/components/ScanPicker";
import { cn, titleCase } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/scans", label: "Scans", icon: ScanLine },
  { to: "/assets", label: "Asset explorer", icon: Boxes },
  { to: "/applications", label: "Applications", icon: AppWindow },
  { to: "/recommendations", label: "Recommendations", icon: ArrowRightLeft },
  { to: "/migration", label: "Migration", icon: KanbanSquare },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/settings", label: "Settings", icon: Settings2, cap: "settings:write" },
];

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setMobileOpen(false), [location.pathname]);
  useEffect(() => {
    if (!mobileOpen) return;
    const close = (event: KeyboardEvent) => event.key === "Escape" && setMobileOpen(false);
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [mobileOpen]);

  return (
    <div className="min-h-screen bg-bg text-text lg:flex">
      <div className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-white/10 bg-black/95 px-4 backdrop-blur lg:hidden">
        <Brand compact />
        <button
          type="button"
          aria-label="Open navigation"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen(true)}
          className="grid h-9 w-9 place-items-center rounded-lg text-muted transition-colors hover:bg-white/[0.06] hover:text-white"
        >
          <Menu size={19} />
        </button>
      </div>

      {mobileOpen && (
        <button
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col border-r border-white/10 bg-black transition-transform duration-200 lg:sticky lg:top-0 lg:h-screen lg:w-64 lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-[72px] items-center justify-between px-5">
          <Brand />
          <button
            type="button"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
            className="grid h-8 w-8 place-items-center rounded-md text-muted hover:bg-white/[0.06] hover:text-white lg:hidden"
          >
            <X size={17} />
          </button>
        </div>
        <SidebarContent />
      </aside>

      <main className="min-w-0 flex-1">
        <ScanPicker />
        <div key={location.pathname} className="page-enter mx-auto w-full max-w-[1600px]">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/15 bg-white text-black">
        <ShieldHalf size={17} strokeWidth={2.2} />
      </div>
      <div className="min-w-0">
        <div className="text-sm font-semibold leading-none tracking-[-0.01em]">ECDAT</div>
        {!compact && <div className="mt-1 text-[10px] tracking-wide text-zinc-500">CRYPTOGRAPHIC INTELLIGENCE</div>}
      </div>
    </div>
  );
}

function SidebarContent() {
  const { me, signOut, can } = useAuth();
  return (
    <>
      <nav aria-label="Primary navigation" className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        <p className="mb-3 px-3 text-[10px] font-medium uppercase tracking-[0.16em] text-zinc-600">Workspace</p>
        {NAV.filter((item) => !item.cap || can(item.cap) || me?.role === "admin").map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => cn(
              "group relative flex h-10 items-center gap-3 rounded-md px-3 text-[13px] font-medium transition-all duration-200 active:scale-[0.99]",
              isActive ? "bg-white/[0.09] text-white" : "text-zinc-500 hover:bg-white/[0.045] hover:text-zinc-200",
            )}
          >
            {({ isActive }) => <>
              {isActive && <span className="absolute left-0 h-4 w-0.5 rounded-full bg-white" />}
              <item.icon size={16} strokeWidth={isActive ? 2 : 1.7} />
              {item.label}
            </>}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-white/10 p-3">
        <div className="flex items-center gap-3 rounded-lg px-3 py-2.5">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white/10 text-xs font-semibold text-white">
            {me?.email?.slice(0, 1).toUpperCase() ?? "·"}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-medium text-zinc-200">{me?.email ?? "Loading…"}</div>
            <div className="mt-0.5 text-[10px] text-zinc-600">{me ? titleCase(me.role) : ""}</div>
          </div>
          <button
            onClick={signOut}
            aria-label="Sign out"
            title="Sign out"
            className="grid h-8 w-8 place-items-center rounded-md text-zinc-500 transition-colors hover:bg-white/[0.06] hover:text-white"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </>
  );
}
