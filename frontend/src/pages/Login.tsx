import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ArrowRight, ShieldHalf } from "lucide-react";
import { useAuth } from "@/store/auth";
import { Button, Input } from "@/components/ui/primitives";

const DEMO = [
  ["admin@ecdat.local", "Administrator"],
  ["analyst@ecdat.local", "Analyst"],
  ["viewer@ecdat.local", "Viewer"],
];

export default function Login() {
  const { signIn, loggedIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@ecdat.local");
  const [password, setPassword] = useState("ecdat");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (loggedIn) return <Navigate to="/" replace />;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email.trim().toLowerCase(), password);
      navigate("/", { replace: true });
    } catch {
      setError("The email or password is incorrect.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-black px-5 py-8 sm:grid sm:place-items-center">
      <div className="mx-auto w-full max-w-[420px] sm:-translate-y-4">
        <div className="mb-10 flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-white text-black">
            <ShieldHalf size={19} strokeWidth={2.2} />
          </div>
          <div>
            <div className="text-sm font-semibold leading-none tracking-tight">ECDAT</div>
            <div className="mt-1 text-[10px] uppercase tracking-[0.15em] text-zinc-600">Cryptographic intelligence</div>
          </div>
        </div>

        <section aria-labelledby="login-title">
          <h1 id="login-title" className="text-3xl font-semibold tracking-[-0.045em] text-white sm:text-4xl">
            Secure access.
          </h1>
          <p className="mt-3 text-sm leading-6 text-zinc-500">
            Sign in to review your organization’s cryptographic posture and migration readiness.
          </p>

          <form onSubmit={submit} className="mt-8 space-y-5">
            <label className="block">
              <span className="mb-2 block text-xs font-medium text-zinc-300">Email address</span>
              <Input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
                required
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-xs font-medium text-zinc-300">Password</span>
              <Input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
                aria-invalid={!!error}
                aria-describedby={error ? "login-error" : undefined}
              />
            </label>
            {error && <p id="login-error" role="alert" className="text-xs text-critical">{error}</p>}
            <Button type="submit" variant="primary" size="lg" className="w-full" disabled={busy}>
              {busy ? "Signing in…" : <>Sign in <ArrowRight size={15} /></>}
            </Button>
          </form>
        </section>

        <div className="mt-10 border-t border-white/10 pt-6">
          <p className="text-[10px] font-medium uppercase tracking-[0.15em] text-zinc-600">Demo access</p>
          <div className="mt-3 grid gap-1">
            {DEMO.map(([demoEmail, role]) => (
              <button
                key={demoEmail}
                type="button"
                onClick={() => setEmail(demoEmail)}
                className="flex items-center justify-between rounded-md px-2 py-2 text-left transition-colors hover:bg-white/[0.05]"
              >
                <span className="font-mono text-[11px] text-zinc-400">{demoEmail}</span>
                <span className="text-[10px] text-zinc-600">{role}</span>
              </button>
            ))}
          </div>
          <p className="mt-3 text-[11px] text-zinc-600">Password for all accounts: <code className="text-zinc-400">ecdat</code></p>
        </div>
      </div>
    </main>
  );
}
