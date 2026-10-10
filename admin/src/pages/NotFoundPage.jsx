import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section>
      <h1>Page not found</h1>
      <p>
        There is no page at this address. <Link to="/">Go to the order list</Link>
      </p>
    </section>
  );
}
