import { Link } from "react-router-dom";

import Button from "../components/Common/Button";
import { APP_ROUTES } from "../utils/constants";

const LandingPage = () => (
  <main className="mx-auto max-w-5xl px-4 py-16">
    <section className="rounded-2xl border border-border bg-bg2 p-8 shadow-sm">
      <p className="font-mono text-xs uppercase tracking-[0.12em] text-accent">Analyze. Understand. Secure.</p>
      <h1 className="mt-3 max-w-3xl text-4xl font-bold leading-tight text-text md:text-5xl">
        Ship safer code with beginner-friendly security explanations.
      </h1>
      <p className="mt-4 max-w-2xl text-base text-text2">
        CodeScan AI reviews your code, highlights real risks, and explains fixes in plain English.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link to={APP_ROUTES.signup}>
          <Button size="lg">Create Free Account</Button>
        </Link>
        <Link to={APP_ROUTES.scan}>
          <Button variant="ghost" size="lg">
            Try Demo Scan
          </Button>
        </Link>
      </div>
    </section>
  </main>
);

export default LandingPage;
