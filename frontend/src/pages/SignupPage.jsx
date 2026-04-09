import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
import { useAuth } from "../hooks/useAuth";
import { APP_ROUTES } from "../utils/constants";

const mapSignupError = (apiError) => {
  if (apiError?.status === 429) {
    return "Too many signup attempts. Please wait a minute before retrying.";
  }
  if (apiError?.status === 409) {
    return "That email is already registered. Try logging in instead.";
  }
  if (apiError?.status === 400) {
    return "Please enter a valid email and a stronger password.";
  }
  if (apiError?.status === 401) {
    return "You are not authorized to perform this action.";
  }
  if (apiError?.status === 404) {
    return "Signup service is unavailable right now.";
  }
  return apiError?.message || "Unable to create account";
};

const SignupPage = () => {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await signUp(form);
      navigate(APP_ROUTES.dashboard, { replace: true });
    } catch (apiError) {
      setError(mapSignupError(apiError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-md px-4 py-12">
      <Card>
        <h1 className="text-xl font-bold">Create Account</h1>
        <form className="mt-4 space-y-3" onSubmit={onSubmit}>
          <input className="w-full rounded-lg border border-border bg-bg3 px-3 py-2" type="email" placeholder="Email" value={form.email} onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))} required />
          <input className="w-full rounded-lg border border-border bg-bg3 px-3 py-2" type="text" placeholder="Username" value={form.username} onChange={(e) => setForm((prev) => ({ ...prev, username: e.target.value }))} />
          <input className="w-full rounded-lg border border-border bg-bg3 px-3 py-2" type="password" placeholder="Password" value={form.password} onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))} required />
          {error ? <p className="text-sm text-red">{error}</p> : null}
          <Button type="submit" className="w-full" isLoading={loading}>Sign Up</Button>
        </form>
        <p className="mt-4 text-sm text-text2">
          Already have an account? <Link to={APP_ROUTES.login} className="text-accent">Login</Link>
        </p>
      </Card>
    </main>
  );
};

export default SignupPage;
