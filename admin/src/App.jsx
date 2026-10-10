import { Suspense, lazy } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import AppShell from "./components/AppShell.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import OrderDetailPage from "./pages/OrderDetailPage.jsx";
import OrderListPage from "./pages/OrderListPage.jsx";

// Optional tools load as a separate chunk; if they are missing or fail, the slot stays empty.
const DemoLauncher = lazy(() => import("./demo/DemoLauncher.jsx"));

export default function App() {
  const location = useLocation();

  return (
    <AppShell
      actions={
        <ErrorBoundary fallback={null}>
          <Suspense fallback={null}>
            <DemoLauncher />
          </Suspense>
        </ErrorBoundary>
      }
    >
      {/* The key resets the boundary when the user navigates away from a broken page. */}
      <ErrorBoundary key={location.pathname}>
        <Routes>
          <Route path="/" element={<OrderListPage />} />
          <Route path="/orders/:id" element={<OrderDetailPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </ErrorBoundary>
    </AppShell>
  );
}
