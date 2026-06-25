import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "@/components/layout/Layout";
import RequireAuth from "@/components/auth/RequireAuth";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import ForwardsList from "@/pages/ForwardsList";
import ForwardEdit from "@/pages/ForwardEdit";
import SourcesList from "@/pages/SourcesList";
import SourceEdit from "@/pages/SourceEdit";
import FolderModal from "@/pages/FolderModal";
import Logs from "@/pages/Logs";
import Settings from "@/pages/Settings";
import FirstRunWizard from "@/pages/FirstRunWizard";

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
        <Route path="forwards/:id" element={<ForwardEdit />} />
        <Route path="sources" element={<SourcesList />} />
        <Route path="sources/:id" element={<SourceEdit />} />
        <Route path="folders/:id" element={<FolderModal />} />
        <Route path="logs" element={<Logs />} />
        <Route path="settings" element={<Settings />} />
        <Route path="wizard" element={<FirstRunWizard />} />
      </Route>
      {/* SPA fallback redirect to dashboard */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
