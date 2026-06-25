import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

export function useKeyboardShortcuts() {
  const navigate = useNavigate();
  const lastKeyRef = useRef<string | null>(null);
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check if focusing an editable field to avoid typing interference
      const activeEl = document.activeElement;
      if (activeEl) {
        const tagName = activeEl.tagName.toLowerCase();
        const isEditable =
          tagName === "input" ||
          tagName === "textarea" ||
          tagName === "select" ||
          activeEl.hasAttribute("contenteditable") ||
          (activeEl as HTMLElement).isContentEditable;
        
        if (isEditable) {
          return;
        }
      }

      const key = e.key.toLowerCase();

      // Vim-style g-based chord detection
      if (lastKeyRef.current === "g") {
        let routed = false;
        if (key === "d") {
          navigate("/");
          routed = true;
        } else if (key === "f") {
          navigate("/forwards");
          routed = true;
        } else if (key === "s") {
          navigate("/sources");
          routed = true;
        } else if (key === "l") {
          navigate("/logs");
          routed = true;
        } else if (key === ",") {
          navigate("/settings");
          routed = true;
        }

        if (routed) {
          e.preventDefault();
        }

        // Reset chord state
        lastKeyRef.current = null;
        if (timeoutRef.current) {
          window.clearTimeout(timeoutRef.current);
        }
      } else if (key === "g") {
        lastKeyRef.current = "g";
        
        // Reset chord after 1000ms
        if (timeoutRef.current) {
          window.clearTimeout(timeoutRef.current);
        }
        timeoutRef.current = window.setTimeout(() => {
          lastKeyRef.current = null;
        }, 1000);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, [navigate]);
}
