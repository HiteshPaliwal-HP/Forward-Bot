import React, { useState, useId } from "react";
import { cn } from "@/lib/utils";

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement<any>;
  className?: string;
}

export function Tooltip({ content, children, className }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const id = useId();

  const handleFocus = () => setVisible(true);
  const handleBlur = () => setVisible(false);

  // Clone children to ensure they have the proper focus handlers if they need them
  // and aria-describedby for accessibility.
  const trigger = React.cloneElement(children, {
    "aria-describedby": visible ? id : undefined,
    onFocus: (e: React.FocusEvent<any>) => {
      handleFocus();
      if (children.props && typeof children.props.onFocus === "function") {
        children.props.onFocus(e);
      }
    },
    onBlur: (e: React.FocusEvent<any>) => {
      handleBlur();
      if (children.props && typeof children.props.onBlur === "function") {
        children.props.onBlur(e);
      }
    }
  });

  return (
    <div 
      className="relative inline-block"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {trigger}
      {visible && (
        <div 
          id={id}
          className={cn(
            "absolute bottom-full left-1/2 z-50 mb-2 w-max max-w-xs -translate-x-1/2 rounded bg-black/90 px-2.5 py-1.5 text-xs text-white shadow-md animate-in fade-in duration-100",
            className
          )}
          role="tooltip"
        >
          {content}
        </div>
      )}
    </div>
  );
}
