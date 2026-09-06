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
    <div className={cn("flex flex-col h-full bg-card text-foreground py-6 px-4 border-r border-border justify-between select-none shadow-xs", className)}>
      <div className="flex flex-col gap-8">
        {/* Logo / Wordmark */}
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold text-lg select-none ring-2 ring-primary/20 shadow-sm">
            F
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight leading-none text-foreground">Forward Bot</h1>
            <span className="text-[9px] font-medium text-muted-foreground tracking-wider uppercase">Operator Panel</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-1">
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
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 select-none",
                    isActive
                      ? "bg-muted text-foreground border-l-2 border-primary pl-2.5 font-semibold"
                      : "text-muted-foreground hover:bg-muted-bg hover:text-foreground"
                  )
                }
              >
                <Icon className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="flex flex-col gap-4">
        <hr className="border-border opacity-60" />
        {/* Theme Select Row */}
        <div className="flex items-center justify-between px-2 text-muted-foreground text-xs">
          <span className="font-medium text-xs">Theme</span>
          <div className="flex bg-muted p-0.5 rounded-lg border border-border">
            <button
              onClick={() => setTheme("light")}
              className={cn(
                "p-1.5 rounded-md transition-all cursor-pointer",
                theme === "light" ? "bg-card text-foreground shadow-sm" : "hover:text-foreground"
              )}
              title="Light theme"
            >
              <Sun className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTheme("dark")}
              className={cn(
                "p-1.5 rounded-md transition-all cursor-pointer",
                theme === "dark" ? "bg-card text-foreground shadow-sm" : "hover:text-foreground"
              )}
              title="Dark theme"
            >
              <Moon className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTheme("system")}
              className={cn(
                "p-1.5 rounded-md transition-all cursor-pointer",
                theme === "system" ? "bg-card text-foreground shadow-sm" : "hover:text-foreground"
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
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-red-500 hover:bg-red-500/10 transition-all cursor-pointer w-full text-left"
        >
          <LogOut className="w-4 h-4" />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
}
