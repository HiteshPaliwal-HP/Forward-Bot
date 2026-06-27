import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, ChevronLeft, ArrowRight, Sparkles, Radio, MessageSquare, ListCollapse } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "./ui/dialog";

interface FirstRunWizardProps {
  open: boolean;
  onDismiss: () => void;
}

export function FirstRunWizard({ open, onDismiss }: FirstRunWizardProps) {
  const [step, setStep] = useState(0);
  const navigate = useNavigate();

  const handleSkip = () => {
    localStorage.setItem("fb-first-run-dismissed", "true");
    onDismiss();
  };

  const handleAction = (path: string) => {
    navigate(path);
    onDismiss();
  };

  const steps = [
    {
      title: "Register a Source",
      description:
        "Connect your Telegram channel, group, or chat as a source. The bot will monitor this source for incoming messages.",
      buttonText: "Go to Sources",
      icon: <Radio className="w-8 h-8 text-primary" />,
      actionPath: "/sources/new",
    },
    {
      title: "Create a Forwarding Rule",
      description:
        "Set up a forwarding rule to forward messages from your sources to destinations. You can apply filters and replacement rules.",
      buttonText: "Go to Forwards",
      icon: <MessageSquare className="w-8 h-8 text-primary" />,
      actionPath: "/forwards/new",
    },
    {
      title: "Verify Live Logs",
      description:
        "Watch live events and forwarding logs as they occur. Check correlation-ID tracing to diagnose forwarding issues in real time.",
      buttonText: "Go to Logs",
      icon: <ListCollapse className="w-8 h-8 text-primary" />,
      actionPath: "/logs",
    },
  ];

  const currentStep = steps[step];

  return (
    <Dialog open={open} onOpenChange={(val) => { if (!val) handleSkip(); }}>
      <DialogHeader>
        <div className="flex items-center space-x-2 text-primary mb-1">
          <Sparkles className="w-4 h-4 text-primary animate-pulse" />
          <span className="text-[10px] font-bold tracking-wider uppercase text-primary">
            Welcome to Forward Bot
          </span>
        </div>
        <DialogTitle>Quick Setup Wizard</DialogTitle>
        <DialogDescription>
          Let's get your Telegram forwarding bot set up in 3 quick steps.
        </DialogDescription>
      </DialogHeader>

      <DialogContent>
        {/* Step indicators */}
        <div className="flex items-center justify-between w-full my-4">
          {steps.map((s, idx) => (
            <React.Fragment key={idx}>
              <div className="flex items-center space-x-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold border transition-all duration-300 ${
                    idx === step
                      ? "bg-primary border-primary text-primary-foreground shadow-sm"
                      : idx < step
                      ? "bg-primary/10 border-primary/20 text-primary"
                      : "bg-muted border-border text-muted-foreground"
                  }`}
                >
                  {idx + 1}
                </div>
                <span
                  className={`text-xs hidden sm:inline font-medium ${
                    idx === step ? "text-foreground font-semibold" : "text-muted-foreground"
                  }`}
                >
                  {s.title}
                </span>
              </div>
              {idx < steps.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-2 transition-all duration-500 ${
                    idx < step ? "bg-primary" : "bg-border"
                  }`}
                />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Step details card */}
        <div className="bg-muted/40 border border-border/80 rounded-xl p-6 flex flex-col items-center text-center space-y-4 transition-all duration-300">
          <div className="p-3 bg-card border border-border rounded-lg shadow-sm">
            {currentStep.icon}
          </div>
          <h3 className="text-base font-semibold text-foreground">{currentStep.title}</h3>
          <p className="text-sm text-muted-foreground max-w-sm">
            {currentStep.description}
          </p>

          <button
            onClick={() => handleAction(currentStep.actionPath)}
            className="w-full flex items-center justify-center space-x-2 py-2 px-4 bg-primary hover:opacity-90 text-primary-foreground font-medium rounded-lg shadow-sm transition-all cursor-pointer text-sm"
          >
            <span>{currentStep.buttonText}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </DialogContent>

      <DialogFooter>
        <div className="flex items-center justify-between w-full mt-4">
          <button
            onClick={handleSkip}
            className="text-xs text-muted-foreground hover:text-primary font-medium transition-colors cursor-pointer"
          >
            Skip setup
          </button>

          <div className="flex space-x-2">
            <button
              onClick={() => setStep((p) => Math.max(0, p - 1))}
              disabled={step === 0}
              className="flex items-center space-x-1 py-1.5 px-3 border border-border text-muted-foreground hover:text-foreground disabled:opacity-50 disabled:hover:text-muted-foreground bg-card hover:bg-muted font-medium text-xs rounded-lg transition-colors cursor-pointer"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Back</span>
            </button>

            {step < steps.length - 1 ? (
              <button
                onClick={() => setStep((p) => Math.min(steps.length - 1, p + 1))}
                className="flex items-center space-x-1 py-1.5 px-3 bg-muted border border-border hover:bg-border text-foreground font-medium text-xs rounded-lg transition-colors cursor-pointer"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                onClick={handleSkip}
                className="flex items-center space-x-1 py-1.5 px-3 bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 font-medium text-xs rounded-lg transition-colors cursor-pointer"
              >
                <span>Finish</span>
              </button>
            )}
          </div>
        </div>
      </DialogFooter>
    </Dialog>
  );
}
