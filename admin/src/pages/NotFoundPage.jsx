import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader.jsx";

export default function NotFoundPage() {
  return (
    <section>
      <PageHeader title="Page not found" />
      <div className="card card-body">
        <p>
          There is no page at this address. <Link to="/">Go to the order list</Link>
        </p>
      </div>
    </section>
  );
}
