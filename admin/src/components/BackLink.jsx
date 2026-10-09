import { Link, useLocation, useNavigate } from "react-router-dom";

const INITIAL_LOCATION_KEY = "default";

export default function BackLink() {
  const location = useLocation();
  const navigate = useNavigate();
  const cameFromApp = location.key !== INITIAL_LOCATION_KEY;

  function handleClick(event) {
    if (!cameFromApp) return;
    event.preventDefault();
    navigate(-1);
  }

  return (
    <Link to="/" className="back-link" onClick={handleClick}>
      ← Back to orders
    </Link>
  );
}
