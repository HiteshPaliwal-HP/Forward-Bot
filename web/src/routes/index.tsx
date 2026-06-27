import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "@/components/layout/Layout";
import RequireAuth from "@/components/auth/RequireAuth";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import ForwardsList from "@/pages/ForwardsList";
import ForwardEdit from "@/pages/ForwardEdit";
import SourcesList from "@/pages/SourcesList";
import SourceEdit from "@/pages/SourceEdit";
import Logs from "@/pages/Logs";
import Settings from "@/pages/Settings";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="forwards" element={<ForwardsList />} />
        <Route path="forwards/new" element={<ForwardEdit />} />
        <Route path="forwards/:id/edit" element={<ForwardEdit />} />
        <Route path="sources" element={<SourcesList />} />
        <Route path="sources/new" element={<SourceEdit />} />
        <Route path="sources/:id/edit" element={<SourceEdit />} />
        <Route path="logs" element={<Logs />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      {/* SPA fallback redirect to dashboard */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
