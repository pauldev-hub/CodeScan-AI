import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";

import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
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
    <main className="mx-auto w-[min(1480px,calc(100vw-24px))] px-3 py-6 md:px-4 md:py-10">
      <ScrollReveal className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
      <Card className="min-h-[520px] overflow-hidden bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01))]">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">Operator login</p>
        <h1 className="mt-4 max-w-md text-4xl font-bold leading-tight text-text">Return to your secure review workspace.</h1>
        <p className="mt-4 max-w-lg text-sm leading-7 text-text2">
          Resume scans, reopen findings, and continue AI-assisted remediation from one editor-style cockpit.
        </p>
        <div className="mt-10 grid gap-3 md:grid-cols-2">
          <div className="rounded-[22px] border border-border bg-bg3/70 p-4">
            <p className="text-[11px] uppercase tracking-[0.16em] text-text3">Workspace</p>
            <p className="mt-2 text-sm font-semibold text-text">Scan, inspect, export</p>
          </div>
          <div className="rounded-[22px] border border-border bg-bg3/70 p-4">
            <p className="text-[11px] uppercase tracking-[0.16em] text-text3">AI assist</p>
            <p className="mt-2 text-sm font-semibold text-text">Clear explanations and fixes</p>
          </div>
        </div>
      </Card>

      <Card className="max-w-xl xl:ml-auto">
        <h1 className="text-xl font-bold">Welcome Back</h1>
        <form className="mt-4 space-y-3" onSubmit={onSubmit}>
          <input className="w-full rounded-2xl border border-border bg-bg3 px-4 py-3" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input className="w-full rounded-2xl border border-border bg-bg3 px-4 py-3" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error ? <p className="text-sm text-red">{error}</p> : null}
          <Button type="submit" className="w-full" isLoading={loading}>
            Login
            <ArrowRight size={16} />
          </Button>
        </form>
        <p className="mt-4 text-sm text-text2">
          New here? <Link to={APP_ROUTES.signup} className="text-accent">Create account</Link>
        </p>
      </Card>
      </ScrollReveal>
    </main>
  );
};

export default LoginPage;
