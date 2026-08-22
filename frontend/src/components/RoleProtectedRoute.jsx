import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { RBAC_MATRIX } from './Sidebar';

export const RoleProtectedRoute = ({ children, routeKey }) => {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div style={{ color: 'white', display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg-main)' }}>Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const allowedRoles = RBAC_MATRIX[routeKey];
  if (allowedRoles && !allowedRoles.includes(user.role.toLowerCase())) {
    // Role not authorized, redirect to an authorized page or a 403 page
    // For simplicity, redirecting to home or the first accessible route
    return <Navigate to="/" replace />;
  }

  return children;
};
