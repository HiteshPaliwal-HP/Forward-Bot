import { NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, ArrowRightLeft, Radio, Terminal, Settings as SettingsIcon, LogOut, Sun, Moon, Laptop } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";
import { cn } from "@/lib/utils";
import { authApi } from "@/api/auth";
import { queryClient } from "@/lib/queryClient";
import { toast } from "sonner";

interface SidebarProps {
  className?: string;
  onItemClick?: () => void;
}

export function Sidebar({ className, onItemClick }: SidebarProps) {
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await authApi.logout();
      queryClient.clear();
      toast.success("Successfully logged out");
      navigate("/login");
    } catch (err) {
      toast.error("Failed to log out");
    }
  };

  const navItems = [
    { label: "Dashboard", path: "/", icon: LayoutDashboard },
    { label: "Forwards", path: "/forwards", icon: ArrowRightLeft },
    { label: "Sources", path: "/sources", icon: Radio },
    { label: "Logs", path: "/logs", icon: Terminal },
    { label: "Settings", path: "/settings", icon: SettingsIcon },
  ];

  return (
    <div className={cn("flex flex-col h-full bg-card text-foreground py-6 px-4 border-r border-border justify-between", className)}>
      <div className="flex flex-col gap-8">
        {/* Logo / Wordmark */}
        <div className="flex items-center gap-2.5 px-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold text-lg select-none">
            F
          </div>
          <div>
            <h1 className="text-md font-semibold tracking-tight leading-none">Forward Bot</h1>
            <span className="text-[10px] text-muted-foreground">Operator Panel</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onItemClick}
                end={item.path === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all duration-200 select-none",
                    isActive
                      ? "bg-primary/10 text-primary font-semibold shadow-xs"
                      : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                  )
                }
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="flex flex-col gap-4">
        <hr className="border-border" />
        {/* Theme Select Row */}
        <div className="flex items-center justify-between px-2 text-muted-foreground text-xs">
          <span className="font-medium">Theme</span>
          <div className="flex bg-muted p-0.5 rounded-md border border-border">
            <button
              onClick={() => setTheme("light")}
              className={cn(
                "p-1.5 rounded-sm transition-colors cursor-pointer",
                theme === "light" ? "bg-card text-primary shadow-xs" : "hover:text-foreground"
              )}
              title="Light theme"
            >
              <Sun className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTheme("dark")}
              className={cn(
                "p-1.5 rounded-sm transition-colors cursor-pointer",
                theme === "dark" ? "bg-card text-primary shadow-xs" : "hover:text-foreground"
              )}
              title="Dark theme"
            >
              <Moon className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTheme("system")}
              className={cn(
                "p-1.5 rounded-sm transition-colors cursor-pointer",
                theme === "system" ? "bg-card text-primary shadow-xs" : "hover:text-foreground"
              )}
              title="System theme"
            >
              <Laptop className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Logout Button */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:text-error hover:bg-error-bg transition-colors cursor-pointer w-full text-left"
        >
          <LogOut className="w-4 h-4" />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
}
