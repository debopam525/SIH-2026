import { createContext, useContext, useEffect } from "react";
import type { ReactNode } from "react";

type Theme = "dark";
const Ctx = createContext<{ theme: Theme; toggle: () => void }>({ theme: "dark", toggle: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    document.documentElement.classList.add("dark");
    localStorage.setItem("ecdat.theme", "dark");
  }, []);
  return (
    <Ctx.Provider value={{ theme: "dark", toggle: () => {} }}>
      {children}
    </Ctx.Provider>
  );
}

export const useTheme = () => useContext(Ctx);
