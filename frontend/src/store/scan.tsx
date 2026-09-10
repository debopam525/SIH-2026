import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

/**
 * Global "active scan" selection. `undefined` means "let the backend use the latest
 * completed scan". A concrete id pins every screen (Dashboard, Asset Explorer,
 * Recommendations, Migration, Reports) to that scan.
 */
interface ScanCtx {
  scanId: string | undefined;
  setScanId: (id: string | undefined) => void;
}

const Ctx = createContext<ScanCtx>({ scanId: undefined, setScanId: () => {} });
const KEY = "ecdat.activeScan";

export function ScanProvider({ children }: { children: ReactNode }) {
  const [scanId, setScanIdState] = useState<string | undefined>(
    () => localStorage.getItem(KEY) || undefined,
  );
  const value = useMemo<ScanCtx>(
    () => ({
      scanId,
      setScanId: (id) => {
        setScanIdState(id);
        try {
          if (id) localStorage.setItem(KEY, id);
          else localStorage.removeItem(KEY);
        } catch {
          /* ignore */
        }
      },
    }),
    [scanId],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useActiveScan = () => useContext(Ctx);
