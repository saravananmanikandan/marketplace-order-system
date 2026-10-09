import { Route, Routes } from "react-router-dom";
import OrderDetailPage from "./pages/OrderDetailPage.jsx";
import OrderListPage from "./pages/OrderListPage.jsx";

export default function App() {
  return (
    <main className="page">
      <Routes>
        <Route path="/" element={<OrderListPage />} />
        <Route path="/orders/:id" element={<OrderDetailPage />} />
      </Routes>
    </main>
  );
}
