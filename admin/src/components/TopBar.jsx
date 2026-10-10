export default function TopBar({ actions }) {
  return (
    <header className="top-bar">
      <span className="top-bar-title">Marketplace Orders</span>
      {actions && <div className="top-bar-actions">{actions}</div>}
    </header>
  );
}
