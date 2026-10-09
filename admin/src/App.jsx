import { Route, Routes } from "react-router-dom";

export default function App() {
  return (
    <main className="page">
      <h1>Marketplace Orders</h1>
      <Routes>
        <Route path="/" element={<p>Orders will appear here.</p>} />
      </Routes>
    </main>
  );
}
