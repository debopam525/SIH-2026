import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { login as apiLogin, tokenStore } from "@/api/client";
import type { Me } from "@/api/types";

interface AuthCtx {
  loggedIn: boolean;
  me: Me | null;
  setMe: (m: Me | null) => void;
  can: (cap: string) => boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [loggedIn, setLoggedIn] = useState(!!tokenStore.access);
  const [me, setMe] = useState<Me | null>(null);

  const value = useMemo<AuthCtx>(
    () => ({
      loggedIn,
      me,
      setMe,
      can: (cap: string) => !!me?.capabilities.includes(cap),
      signIn: async (email: string, password: string) => {
        await apiLogin(email, password);
        setLoggedIn(true);
      },
      signOut: () => {
        tokenStore.clear();
        setLoggedIn(false);
        setMe(null);
        qc.clear();
      },
    }),
    [loggedIn, me, qc],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside AuthProvider");
  return c;
}
