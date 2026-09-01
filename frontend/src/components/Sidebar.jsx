import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  Activity, 
  ClipboardCheck, 
  Database, 
  Users,
  MessageSquare,
  UploadCloud,
  LogOut
} from 'lucide-react';

// Source of truth mapping route keys to allowed roles, reflecting backend rbac.py
export const RBAC_MATRIX = {
  intake: ['doctor', 'nurse', 'hospital_admin'],
  review: ['doctor', 'nurse', 'hospital_admin'],
  canonical: ['doctor', 'nurse', 'hospital_admin'],
  patients: ['doctor', 'nurse', 'hospital_admin'],
  dashboards: ['hospital_admin', 'department_head'],
  policyChat: ['doctor', 'nurse', 'hospital_admin'],
  policyUpload: ['hospital_admin', 'it', 'compliance'],
};

const hasAccess = (role, routeKey) => {
  return RBAC_MATRIX[routeKey]?.includes(role.toLowerCase());
};

export default function Sidebar() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <aside className="app-sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">
          <Activity size={24} color="#ffffff" />
        </div>
        <div className="brand-text">
          <span>Clinical</span>
          <span style={{ color: 'var(--primary-cyan)', fontWeight: 700 }}>Intelligence</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {hasAccess(user.role, 'intake') && (
          <NavLink to="/intake" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <Activity size={18} />
            <span>Document Intake</span>
          </NavLink>
        )}
        
        {hasAccess(user.role, 'review') && (
          <NavLink to="/review" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <ClipboardCheck size={18} />
            <span>Review Queue</span>
          </NavLink>
        )}
        
        {hasAccess(user.role, 'patients') && (
          <NavLink to="/patients" className={({ isActive }) => `sidebar-link ${isActive || window.location.pathname.startsWith('/patients/') ? 'active' : ''}`}>
            <Users size={18} />
            <span>Patients</span>
          </NavLink>
        )}

        {hasAccess(user.role, 'dashboards') && (
          <NavLink to="/operations-dashboard" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <Activity size={18} />
            <span>Operations Dashboard</span>
          </NavLink>
        )}

        <div className="sidebar-divider"></div>
        <div className="sidebar-section-title">Tools</div>

        {hasAccess(user.role, 'patients') && (
          <NavLink to="/patients/ask" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <MessageSquare size={18} />
            <span>Patient Q&A</span>
          </NavLink>
        )}

        {hasAccess(user.role, 'policyChat') && (
          <NavLink to="/policy-assistant" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <MessageSquare size={18} />
            <span>Policy Assistant</span>
          </NavLink>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="user-info">
            <span className="user-email">{user.email}</span>
            <span className="user-role">{user.role}</span>
          </div>
          <button onClick={logout} className="logout-btn" title="Logout">
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}
