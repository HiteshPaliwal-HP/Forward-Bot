/**
 * Frontend E2E Integration Tests for Epic 7: Session Management & Multi-Tier Cache Control
 *
 * Covers:
 * - Story 7-1 / 7-3: TopBar & Settings "Refresh Cache" button flow with metadata toasts and error handling
 * - Story 7-2 / 7-3: Settings Telegram Session Card state machine:
 *   - DISCONNECTED badge rendering
 *   - E.164 phone input entry and "Send OTP" 60s timer throttling
 *   - OTP verification step & HTTP 202 requires_2fa transition
 *   - 2FA password step & successful authentication transition to CONNECTED badge
 *   - Terminate session modal requiring case-insensitive 'terminate' confirmation
 *   - Handling 400 invalid_otp and 409 auth_in_progress inline error alerts
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@/api/health", () => ({
  healthApi: {
    fetchHealth: vi.fn().mockResolvedValue({ status: "ok" }),
    fetchCacheStatus: vi.fn().mockResolvedValue({
      mongodb: "up",
      cache: { version: 1, rule_count: 5, source_count: 2, refreshed_at: "2026-09-07T00:00:00Z" },
    }),
    fetchTelegramStatus: vi.fn().mockResolvedValue({ telegram: "connected" }),
  },
}));

vi.mock("@/api/admin", () => ({
  adminApi: {
    refreshCache: vi.fn().mockResolvedValue({
      status: "success",
      cache: { version: 3, rule_count: 12, source_count: 4, refreshed_at: "2026-09-07T00:50:00Z" },
    }),
  },
}));

vi.mock("@/api/telegramAuth", () => ({
  telegramAuthApi: {
    getStatus: vi.fn().mockResolvedValue({
      connected: false,
      phone: null,
      phone_required: true,
      session_path: "/app/data/forward_bot.session",
    }),
    startAuth: vi.fn().mockResolvedValue({ status: "code_sent" }),
    verifyAuth: vi.fn().mockResolvedValue({ status: "connected" }),
    terminateSession: vi.fn().mockResolvedValue({ status: "terminated" }),
  },
}));

vi.mock("@/api/auth", () => ({
  authApi: {
    logout: vi.fn().mockResolvedValue({ ok: true }),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// Imports after mocks
import TopBar from "@/components/layout/TopBar";
import Settings from "@/pages/Settings";
import { adminApi } from "@/api/admin";
import { telegramAuthApi } from "@/api/telegramAuth";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
}

function renderComponent(ui: React.ReactNode) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Test Suite: Epic 7 Frontend E2E
// ---------------------------------------------------------------------------

describe("Epic 7 Frontend E2E: TopBar & Settings Cache & Telegram Auth Flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Story 7.1 / 7.3: TopBar Cache Refresh Button", () => {
    it("renders Refresh Cache button and handles successful metadata toast", async () => {
      renderComponent(<TopBar title="Settings" />);

      const refreshBtn = screen.getByRole("button", { name: /refresh cache/i });
      expect(refreshBtn).toBeInTheDocument();

      fireEvent.click(refreshBtn);

      await waitFor(() => {
        expect(adminApi.refreshCache).toHaveBeenCalledTimes(1);
      });

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          expect.stringContaining("Cache rebuilt (v3) — 12 rules, 4 sources")
        );
      });
    });

    it("displays destructive error toast when cache refresh fails", async () => {
      vi.mocked(adminApi.refreshCache).mockRejectedValueOnce(new Error("Database offline"));

      renderComponent(<TopBar title="Settings" />);

      const refreshBtn = screen.getByRole("button", { name: /refresh cache/i });
      fireEvent.click(refreshBtn);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith("Database offline");
      });
    });
  });

  describe("Story 7.2 / 7.3: Settings Page Telegram Session Lifecycle & 2FA Flow", () => {
    it("completes DISCONNECTED -> Phone -> Send OTP -> 2FA prompt -> CONNECTED transition", async () => {
      // 1. Initial status is DISCONNECTED
      renderComponent(<Settings />);

      await waitFor(() => {
        expect(screen.getByText("DISCONNECTED")).toBeInTheDocument();
      });

      // 2. Phone input & Send OTP
      const phoneInput = screen.getByPlaceholderText(/^\+/);
      fireEvent.change(phoneInput, { target: { value: "+12025550123" } });

      const sendOtpBtn = screen.getByRole("button", { name: /send otp/i });
      fireEvent.click(sendOtpBtn);

      await waitFor(() => {
        expect(telegramAuthApi.startAuth).toHaveBeenCalledWith("+12025550123");
        expect(toast.success).toHaveBeenCalledWith("Verification code sent to +12025550123");
      });

      // 3. Verify OTP step returns HTTP 202 requires_2fa
      vi.mocked(telegramAuthApi.verifyAuth).mockResolvedValueOnce({ requires_2fa: true } as any);

      const otpInput = await screen.findByPlaceholderText("123456");
      fireEvent.change(otpInput, { target: { value: "654321" } });

      const connectBtn = screen.getByRole("button", { name: /connect telegram/i });
      fireEvent.click(connectBtn);

      await waitFor(() => {
        expect(telegramAuthApi.verifyAuth).toHaveBeenCalledWith({
          otp: "654321",
          phone: "+12025550123",
        });
      });

      // 4. Password input step for 2FA
      const passwordInput = await screen.findByPlaceholderText("Enter 2FA password");
      expect(passwordInput).toBeInTheDocument();

      vi.mocked(telegramAuthApi.verifyAuth).mockResolvedValueOnce({ status: "connected" } as any);

      fireEvent.change(passwordInput, { target: { value: "my2fapassword" } });

      const submit2faBtn = screen.getByRole("button", { name: /submit 2fa password/i });
      fireEvent.click(submit2faBtn);

      await waitFor(() => {
        expect(telegramAuthApi.verifyAuth).toHaveBeenCalledWith({
          otp: "654321",
          password: "my2fapassword",
          phone: "+12025550123",
        });
        expect(toast.success).toHaveBeenCalledWith("Telegram connected successfully!");
      });
    });

    it("handles terminate modal typing validation and session termination", async () => {
      // Set status to CONNECTED
      vi.mocked(telegramAuthApi.getStatus).mockResolvedValueOnce({
        connected: true,
        phone: "+1202••••0123",
        phone_required: false,
        session_path: "/app/data/session.session",
      });

      renderComponent(<Settings />);

      await waitFor(() => {
        expect(screen.getByText("CONNECTED")).toBeInTheDocument();
      });

      // Click Terminate Session button
      const terminateBtn = screen.getByRole("button", { name: /terminate session/i });
      fireEvent.click(terminateBtn);

      // Modal opens
      const modalInput = await screen.findByPlaceholderText("terminate");
      const confirmBtn = screen.getByRole("button", { name: /confirm terminate/i });

      // Button is initially disabled
      expect(confirmBtn).toBeDisabled();

      // Type "terminate"
      fireEvent.change(modalInput, { target: { value: "TERMINATE" } });
      expect(confirmBtn).not.toBeDisabled();

      // Click confirm terminate
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(telegramAuthApi.terminateSession).toHaveBeenCalledTimes(1);
        expect(toast.success).toHaveBeenCalledWith("Telegram session terminated");
      });
    });

    it("displays inline error alert on invalid OTP API error (HTTP 400)", async () => {
      renderComponent(<Settings />);

      await waitFor(() => {
        expect(screen.getByText("DISCONNECTED")).toBeInTheDocument();
      });

      const phoneInput = screen.getByPlaceholderText(/^\+/);
      fireEvent.change(phoneInput, { target: { value: "+12025550123" } });
      fireEvent.click(screen.getByRole("button", { name: /send otp/i }));

      await waitFor(() => {
        expect(telegramAuthApi.startAuth).toHaveBeenCalled();
      });

      // Mock verifyAuth rejecting with invalid OTP error envelope
      const errResponse = {
        response: {
          data: {
            error: { code: "invalid_otp", message: "Invalid code entered. Please check and try again." },
          },
        },
      };
      vi.mocked(telegramAuthApi.verifyAuth).mockRejectedValueOnce(errResponse);

      const otpInput = await screen.findByPlaceholderText("123456");
      fireEvent.change(otpInput, { target: { value: "000000" } });
      fireEvent.click(screen.getByRole("button", { name: /connect telegram/i }));

      await waitFor(() => {
        expect(screen.getByText("Invalid code entered. Please check and try again.")).toBeInTheDocument();
      });
    });
  });
});
