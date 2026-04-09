import { Navigate } from "react-router-dom";

import { APP_ROUTES } from "../utils/constants";
import { useAuth } from "../hooks/useAuth";

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to={APP_ROUTES.login} replace />;
  }
  return children;
};

export default ProtectedRoute;
