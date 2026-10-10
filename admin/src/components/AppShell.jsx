import { Link } from "react-router-dom";
import { ORDERS_PATH } from "../constants.js";

export default function AppShell({ actions, children }) {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link to={ORDERS_PATH} className="topbar-name">
            Marketplace Orders
          </Link>
          <div className="topbar-actions">{actions}</div>
        </div>
      </header>
      <main className="main">
        <div className="main-inner">{children}</div>
      </main>
    </div>
  );
}
