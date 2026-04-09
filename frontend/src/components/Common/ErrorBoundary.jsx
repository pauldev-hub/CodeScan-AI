import { Component } from "react";

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      message: "",
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      message: error?.message || "Unexpected UI failure",
    };
  }

  componentDidCatch(error, info) {
    if (this.props.onError) {
      this.props.onError(error, info);
    }
  }

  reset = () => {
    this.setState({ hasError: false, message: "" });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback({ message: this.state.message, reset: this.reset });
    }

    return (
      <div className="rounded-[10px] border border-red/50 bg-red/10 p-4 text-sm text-red">
        <p className="font-semibold">Something went wrong in this section.</p>
        <p className="mt-1">{this.state.message}</p>
        <button type="button" className="mt-3 rounded-md border border-red px-3 py-1" onClick={this.reset}>
          Try again
        </button>
      </div>
    );
  }
}

export default ErrorBoundary;
