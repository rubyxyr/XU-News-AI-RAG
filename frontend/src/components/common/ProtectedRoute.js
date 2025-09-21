import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAppSelector } from '../../hooks/redux';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAppSelector((state) => state.auth);
  const location = useLocation();

  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <div className="loading-text">Verifying authentication...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login page with return URL
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

export default ProtectedRoute;
