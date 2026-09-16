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
  LogOut,
  BarChart2
} from 'lucide-react';

export const RBAC_MATRIX = {
  intake: ['doctor', 'nurse', 'hospital_admin'],
  review: ['doctor', 'nurse', 'hospital_admin'],
  canonical: ['doctor', 'nurse', 'hospital_admin'],
  patients: ['doctor', 'nurse', 'hospital_admin'],
  patientDashboard: ['doctor', 'hospital_admin'],
  dashboards: ['hospital_admin', 'department_head'],
  policyChat: ['doctor', 'nurse', 'hospital_admin'],
  policyUpload: ['hospital_admin', 'it', 'compliance'],
  patientQA: ['doctor'],
  reports: ['doctor', 'hospital_admin'],
};

const hasAccess = (role, routeKey) => {
  return RBAC_MATRIX[routeKey]?.includes(role.toLowerCase());
};

export default function Sidebar() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <aside className="w-64 flex-shrink-0 flex flex-col bg-surface border-r border-line h-screen">
      <div className="flex items-center gap-3 p-6 border-b border-line">
        <div className="w-10 h-10 rounded-xl bg-teal flex items-center justify-center text-white">
          <Activity size={24} />
        </div>
        <div className="text-xl font-sans tracking-tight">
          <span className="text-ink font-medium">Clinical</span>
          <span className="text-teal font-bold">Intelligence</span>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-6 px-4 flex flex-col gap-1">
        {hasAccess(user.role, 'intake') && (
          <NavLink to="/intake" className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-md font-medium text-sm transition-colors ${isActive ? 'text-teal bg-teal/10' : 'text-ink hover:bg-paper'}`}>
            <Activity size={18} />
            <span>Document Intake</span>
          </NavLink>
        )}
        
        {hasAccess(user.role, 'review') && (
          <NavLink to="/review" className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-md font-medium text-sm transition-colors ${isActive ? 'text-teal bg-teal/10' : 'text-ink hover:bg-paper'}`}>
            <ClipboardCheck size={18} />
            <span>Review Queue</span>
          </NavLink>
        )}
        
        {hasAccess(user.role, 'patients') && (
          <NavLink to="/patients" className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-md font-medium text-sm transition-colors ${isActive || window.location.pathname.startsWith('/patients/') ? 'text-teal bg-teal/10' : 'text-ink hover:bg-paper'}`}>
            <Users size={18} />
            <span>Patients</span>
          </NavLink>
        )}

        {hasAccess(user.role, 'dashboards') && (
          <NavLink to="/operations-dashboard" className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-md font-medium text-sm transition-colors ${isActive ? 'text-teal bg-teal/10' : 'text-ink hover:bg-paper'}`}>
            <BarChart2 size={18} />
            <span>Operations Dashboard</span>
          </NavLink>
        )}

        {hasAccess(user.role, 'reports') && (
          <NavLink to="/reports" className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-md font-medium text-sm transition-colors ${isActive ? 'text-teal bg-teal/10' : 'text-ink hover:bg-paper'}`}>
            <BarChart2 size={18} />
            <span>Report Builder</span>
          </NavLink>
        )}

        <div className="my-4 border-t border-line"></div>
        <div className="px-3 mb-2 text-xs font-medium text-slate">Tools</div>

        {hasAccess(user.role, 'patientQA') && (
          <NavLink to="/patients/ask" className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-md font-medium text-sm transition-colors ${isActive ? 'text-teal bg-teal/10' : 'text-ink hover:bg-paper'}`}>
            <MessageSquare size={18} />
            <span>Patient Q&A</span>
          </NavLink>
        )}

        {hasAccess(user.role, 'policyChat') && (
          <NavLink to="/policy-assistant" className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-md font-medium text-sm transition-colors ${isActive ? 'text-teal bg-teal/10' : 'text-ink hover:bg-paper'}`}>
            <MessageSquare size={18} />
            <span>Policy Assistant</span>
          </NavLink>
        )}
      </nav>

      <div className="p-4 border-t border-line flex items-center justify-between">
        <div className="flex flex-col overflow-hidden mr-2">
          <span className="text-sm font-medium text-ink truncate">{user.email}</span>
          <span className="text-xs text-slate capitalize">{user.role}</span>
        </div>
        <button onClick={logout} className="p-2 text-slate hover:text-ink hover:bg-paper rounded-md transition-colors flex-shrink-0" title="Logout">
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
