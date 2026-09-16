import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout() {
  return (
    <div className="min-h-screen flex bg-paper text-ink font-sans">
      <Sidebar />
      <main className="flex-1 h-screen overflow-y-auto p-margin-mobile md:p-margin-desktop w-full">
        <Outlet />
      </main>
    </div>
  );
}
