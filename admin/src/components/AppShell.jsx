import { Link, useLocation } from "react-router-dom";

const ORDERS_PATH = "/";
const ORDER_DETAIL_PREFIX = "/orders/";

export default function AppShell({ actions, children }) {
  const { pathname } = useLocation();
  const onOrders = pathname === ORDERS_PATH || pathname.startsWith(ORDER_DETAIL_PREFIX);

  return (
    <div className="shell">
      <aside className="sidebar">
        <span className="sidebar-name">Marketplace Orders</span>
        <nav className="sidebar-nav" aria-label="Main">
          <Link
            to={ORDERS_PATH}
            className="sidebar-link"
            aria-current={onOrders ? "page" : undefined}
          >
            Orders
          </Link>
        </nav>
        <div className="sidebar-actions">{actions}</div>
      </aside>
      <main className="main">
        <div className="main-inner">{children}</div>
      </main>
    </div>
  );
}
