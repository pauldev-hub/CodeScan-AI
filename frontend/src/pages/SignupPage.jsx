import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";

import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
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
    <main className="mx-auto w-[min(1480px,calc(100vw-24px))] px-3 py-6 md:px-4 md:py-10">
      <ScrollReveal className="grid gap-5 xl:grid-cols-[0.96fr_1.04fr]">
      <Card className="max-w-xl xl:order-2">
        <h1 className="text-xl font-bold">Create Account</h1>
        <form className="mt-4 space-y-3" onSubmit={onSubmit}>
          <input className="w-full rounded-2xl border border-border bg-bg3 px-4 py-3" type="email" placeholder="Email" value={form.email} onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))} required />
          <input className="w-full rounded-2xl border border-border bg-bg3 px-4 py-3" type="text" placeholder="Username" value={form.username} onChange={(e) => setForm((prev) => ({ ...prev, username: e.target.value }))} />
          <input className="w-full rounded-2xl border border-border bg-bg3 px-4 py-3" type="password" placeholder="Password" value={form.password} onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))} required />
          {error ? <p className="text-sm text-red">{error}</p> : null}
          <Button type="submit" className="w-full" isLoading={loading}>
            Sign Up
            <ArrowRight size={16} />
          </Button>
        </form>
        <p className="mt-4 text-sm text-text2">
          Already have an account? <Link to={APP_ROUTES.login} className="text-accent">Login</Link>
        </p>
      </Card>

      <Card className="min-h-[520px] overflow-hidden bg-[linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01))] xl:order-1">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">Create your cockpit</p>
        <h1 className="mt-4 max-w-md text-4xl font-bold leading-tight text-text">Set up a premium code review workspace in minutes.</h1>
        <p className="mt-4 max-w-lg text-sm leading-7 text-text2">
          Keep scans, AI guidance, reports, and fixes in one shared environment built for safer shipping and faster triage.
        </p>
        <div className="mt-10 space-y-3">
          <div className="rounded-[22px] border border-border bg-bg3/70 p-4">
            <p className="text-[11px] uppercase tracking-[0.16em] text-text3">Included</p>
            <p className="mt-2 text-sm font-semibold text-text">Repository scans, pasted code reviews, and AI follow-up.</p>
          </div>
          <div className="rounded-[22px] border border-border bg-bg3/70 p-4">
            <p className="text-[11px] uppercase tracking-[0.16em] text-text3">Built for</p>
            <p className="mt-2 text-sm font-semibold text-text">Students, solo builders, and teams that want clear security feedback.</p>
          </div>
        </div>
      </Card>
      </ScrollReveal>
    </main>
  );
};

export default SignupPage;
