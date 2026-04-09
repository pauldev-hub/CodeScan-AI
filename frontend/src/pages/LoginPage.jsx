import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
import { useAuth } from "../hooks/useAuth";
import { APP_ROUTES } from "../utils/constants";

const mapLoginError = (apiError) => {
  if (apiError?.status === 429) {
    return "Too many login attempts. Wait a minute and try again.";
  }
  if (apiError?.status === 409) {
    return "Login request conflicted with current account state. Try again.";
  }
  if (apiError?.status === 404) {
    return "No account found for this email.";
  }
  if (apiError?.status === 401) {
    return "Email or password is incorrect.";
  }
  if (apiError?.status === 400) {
    return "Please check your email and password format.";
  }
  return apiError?.message || "Unable to log in";
};

const LoginPage = () => {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await signIn({ email, password });
      navigate(APP_ROUTES.dashboard, { replace: true });
    } catch (apiError) {
      setError(mapLoginError(apiError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-md px-4 py-12">
      <Card>
        <h1 className="text-xl font-bold">Welcome Back</h1>
        <form className="mt-4 space-y-3" onSubmit={onSubmit}>
          <input className="w-full rounded-lg border border-border bg-bg3 px-3 py-2" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input className="w-full rounded-lg border border-border bg-bg3 px-3 py-2" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error ? <p className="text-sm text-red">{error}</p> : null}
          <Button type="submit" className="w-full" isLoading={loading}>Login</Button>
        </form>
        <p className="mt-4 text-sm text-text2">
          New here? <Link to={APP_ROUTES.signup} className="text-accent">Create account</Link>
        </p>
      </Card>
    </main>
  );
};

export default LoginPage;
