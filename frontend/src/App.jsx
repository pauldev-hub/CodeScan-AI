import { useState } from "react";
import { Route, Routes } from "react-router-dom";

import ErrorBoundary from "./components/Common/ErrorBoundary";
import SplashScreen from "./components/Common/SplashScreen";
import Navbar from "./components/Layout/Navbar";
import Sidebar from "./components/Layout/Sidebar";
import AdminDashboardPage from "./pages/admin/AdminDashboardPage";
import AdminIncidentsPage from "./pages/admin/AdminIncidentsPage";
import AdminQueuePage from "./pages/admin/AdminQueuePage";
import DashboardPage from "./pages/DashboardPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import ResultsPage from "./pages/ResultsPage";
import ScanPage from "./pages/ScanPage";
import SharedReportPage from "./pages/SharedReportPage";
import SignupPage from "./pages/SignupPage";
import AdminRoute from "./routes/AdminRoute";
import ProtectedRoute from "./routes/ProtectedRoute";
import PublicOnlyRoute from "./routes/PublicOnlyRoute";
import { APP_ROUTES } from "./utils/constants";

const ProtectedLayout = ({ children }) => {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <div className="codescan-shell theme-transition">
      <Navbar onMenuToggle={() => setMobileSidebarOpen((open) => !open)} showMenuButton />
      <div className="mx-auto grid max-w-[1400px] grid-cols-1 md:grid-cols-[64px_1fr] xl:grid-cols-[200px_1fr]">
        <Sidebar mobileOpen={mobileSidebarOpen} onClose={() => setMobileSidebarOpen(false)} />
        <section className="p-4">{children}</section>
      </div>
    </div>
  );
};

const PublicLayout = ({ children }) => (
  <div className="codescan-shell theme-transition">
    <Navbar />
    {children}
  </div>
);

const App = () => {
  const [showSplash, setShowSplash] = useState(true);

  return (
    <ErrorBoundary>
      {showSplash ? <SplashScreen onDone={() => setShowSplash(false)} /> : null}
      <Routes>
      <Route
        path={APP_ROUTES.landing}
        element={
          <PublicLayout>
            <LandingPage />
          </PublicLayout>
        }
      />

      <Route
        path={APP_ROUTES.login}
        element={
          <PublicOnlyRoute>
            <PublicLayout>
              <LoginPage />
            </PublicLayout>
          </PublicOnlyRoute>
        }
      />

      <Route
        path={APP_ROUTES.signup}
        element={
          <PublicOnlyRoute>
            <PublicLayout>
              <SignupPage />
            </PublicLayout>
          </PublicOnlyRoute>
        }
      />

      <Route
        path={APP_ROUTES.dashboard}
        element={
          <ProtectedRoute>
            <ProtectedLayout>
              <DashboardPage />
            </ProtectedLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path={APP_ROUTES.scan}
        element={
          <ProtectedRoute>
            <ProtectedLayout>
              <ScanPage />
            </ProtectedLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path={APP_ROUTES.results}
        element={
          <ProtectedRoute>
            <ProtectedLayout>
              <ResultsPage />
            </ProtectedLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path={APP_ROUTES.sharedReport}
        element={
          <PublicLayout>
            <SharedReportPage />
          </PublicLayout>
        }
      />

      <Route
        path={APP_ROUTES.admin}
        element={
          <AdminRoute>
            <ProtectedLayout>
              <AdminDashboardPage />
            </ProtectedLayout>
          </AdminRoute>
        }
      />

      <Route
        path={APP_ROUTES.adminQueue}
        element={
          <AdminRoute>
            <ProtectedLayout>
              <AdminQueuePage />
            </ProtectedLayout>
          </AdminRoute>
        }
      />

      <Route
        path={APP_ROUTES.adminIncidents}
        element={
          <AdminRoute>
            <ProtectedLayout>
              <AdminIncidentsPage />
            </ProtectedLayout>
          </AdminRoute>
        }
      />

      <Route
        path="*"
        element={
          <PublicLayout>
            <NotFoundPage />
          </PublicLayout>
        }
      />
      </Routes>
    </ErrorBoundary>
  );
};

export default App;
