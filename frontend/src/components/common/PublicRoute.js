import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAppSelector } from '../../hooks/redux';

const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAppSelector((state) => state.auth);

  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <div className="loading-text">Loading...</div>
      </div>
    );
  }

  if (isAuthenticated) {
    // If user is already authenticated, redirect to dashboard
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

export default PublicRoute;
