import { Component } from "react";
import { Link } from "react-router-dom";

// React can only catch render errors in a class component.
export default class ErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="message" role="alert">
        Something went wrong while showing this page. <Link to="/">Go to the order list</Link>
      </div>
    );
  }
}
