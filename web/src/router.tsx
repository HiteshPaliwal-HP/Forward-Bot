import { createBrowserRouter } from "react-router-dom";

import Layout from "@/components/layout/Layout";
import Dashboard from "@/pages/Dashboard";
import ForwardsList from "@/pages/ForwardsList";
import ForwardEdit from "@/pages/ForwardEdit";
import SourcesList from "@/pages/SourcesList";
import SourceEdit from "@/pages/SourceEdit";
import FolderModal from "@/pages/FolderModal";
import Logs from "@/pages/Logs";
import Settings from "@/pages/Settings";
import FirstRunWizard from "@/pages/FirstRunWizard";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    errorElement: (
      <div style={{ padding: "2rem", textAlign: "center", color: "#ef4444" }}>
        <h1>Something went wrong</h1>
        <p>An unexpected routing error occurred.</p>
        <button onClick={() => window.location.href = "/"} style={{ marginTop: "1rem", padding: "0.5rem 1rem", cursor: "pointer" }}>
          Go to Dashboard
        </button>
      </div>
    ),
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: "forwards",
        element: <ForwardsList />,
      },
      {
        path: "forwards/:id",
        element: <ForwardEdit />,
      },
      {
        path: "sources",
        element: <SourcesList />,
      },
      {
        path: "sources/:id",
        element: <SourceEdit />,
      },
      {
        path: "folders/:id",
        element: <FolderModal />,
      },
      {
        path: "logs",
        element: <Logs />,
      },
      {
        path: "settings",
        element: <Settings />,
      },
      {
        path: "wizard",
        element: <FirstRunWizard />,
      },
    ],
  },
]);
