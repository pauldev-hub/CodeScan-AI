import { Navigate } from "react-router-dom";

import { APP_ROUTES } from "../utils/constants";
import { useAuth } from "../hooks/useAuth";

const AdminRoute = ({ children }) => {
  const { isAuthenticated, user } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to={APP_ROUTES.login} replace />;
  }

  if (user?.role !== "admin") {
    return <Navigate to={APP_ROUTES.dashboard} replace />;
  }

  return children;
};

export default AdminRoute;
