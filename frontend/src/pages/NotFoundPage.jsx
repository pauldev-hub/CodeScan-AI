import { Link } from "react-router-dom";

import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
import { APP_ROUTES } from "../utils/constants";

const NotFoundPage = () => (
  <main className="mx-auto max-w-lg px-4 py-16">
    <Card className="text-center">
      <p className="font-mono text-xs uppercase tracking-[0.12em] text-accent">404</p>
      <h1 className="mt-2 text-2xl font-bold">Page not found</h1>
      <p className="mt-2 text-sm text-text2">The route you opened does not exist or was moved.</p>
      <Link className="mt-5 inline-block" to={APP_ROUTES.landing}>
        <Button>Go Home</Button>
      </Link>
    </Card>
  </main>
);

export default NotFoundPage;
