import { Route, Routes } from "react-router-dom";
import OrderListPage from "./pages/OrderListPage.jsx";

export default function App() {
  return (
    <main className="page">
      <Routes>
        <Route path="/" element={<OrderListPage />} />
      </Routes>
    </main>
  );
}
