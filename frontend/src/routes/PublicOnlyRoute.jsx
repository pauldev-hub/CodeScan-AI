import { Navigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { APP_ROUTES } from "../utils/constants";

const PublicOnlyRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to={APP_ROUTES.dashboard} replace />;
  }

  return children;
};

export default PublicOnlyRoute;
