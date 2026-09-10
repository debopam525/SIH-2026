import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useMe } from "./api/hooks";
import { useAuth } from "./store/auth";
import { AppShell } from "./components/layout/AppShell";
import { Skeleton } from "./components/ui/primitives";

const Login = lazy(() => import("./pages/Login"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Scans = lazy(() => import("./pages/Scans"));
const Assets = lazy(() => import("./pages/Assets"));
const RiskDetail = lazy(() => import("./pages/RiskDetail"));
const Applications = lazy(() => import("./pages/Applications"));
const Recommendations = lazy(() => import("./pages/Recommendations"));
const Migration = lazy(() => import("./pages/Migration"));
const Reports = lazy(() => import("./pages/Reports"));
const Settings = lazy(() => import("./pages/Settings"));

function Protected({ children }: { children: JSX.Element }) {
  const { loggedIn, setMe } = useAuth();
  const loc = useLocation();
  const me = useMe();
  useEffect(() => {
    if (me.data) setMe(me.data);
  }, [me.data, setMe]);
  if (!loggedIn) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  return children;
}

export default function App() {
  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <Protected>
              <AppShell />
            </Protected>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="/scans" element={<Scans />} />
          <Route path="/assets" element={<Assets />} />
          <Route path="/assets/:assetId" element={<RiskDetail />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/applications/:appId" element={<Applications />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/migration" element={<Migration />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

function PageLoading() {
  return (
    <div className="grid min-h-screen place-items-center bg-black px-6" role="status" aria-label="Loading page">
      <div className="w-full max-w-sm space-y-3">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-4/5" />
      </div>
    </div>
  );
}
