import { Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Navigation placeholder */}
      <nav className="bg-card border-b border-border px-4 py-3">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold">Forward Bot</h1>
        </div>
      </nav>

      {/* Main content area */}
      <main className="flex-1 px-4 py-6">
        <div className="max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>

      {/* Footer placeholder */}
      <footer className="bg-card border-t border-border px-4 py-3 text-sm text-muted-foreground">
        <div className="max-w-7xl mx-auto">
          Forward Bot — self-hosted Telegram forwarding
        </div>
      </footer>
    </div>
  );
}
