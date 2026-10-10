import { Route, Routes, useLocation } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import OrderDetailPage from "./pages/OrderDetailPage.jsx";
import OrderListPage from "./pages/OrderListPage.jsx";

export default function App() {
  const location = useLocation();

  return (
    <main className="page">
      {/* The key resets the boundary when the user navigates away from a broken page. */}
      <ErrorBoundary key={location.pathname}>
        <Routes>
          <Route path="/" element={<OrderListPage />} />
          <Route path="/orders/:id" element={<OrderDetailPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </ErrorBoundary>
    </main>
  );
}
