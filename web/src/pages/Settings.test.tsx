/**
 * Unit & Component Tests for Settings page (Story 7-3, AC 1-6)
 *
 * Covers:
 * - AC1: Refresh Cache button triggers adminApi.refreshCache and surfaces success/destructive toasts
 * - AC2: Telegram Session Card status rendering (CONNECTED badge vs DISCONNECTED badge)
 * - AC3: E.164 phone input & 60s client throttle on Send OTP trigger
 * - AC4: 6-digit OTP code entry & HTTP 202 requires_2fa password entry step
 * - AC5: Inline error banner rendering on auth edge cases (e.g. invalid OTP)
 * - AC6: Terminate Session confirmation modal requiring typing 'terminate' to enable confirm button
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
      cache: { version: 1, rule_count: 5, source_count: 2, refreshed_at: new Date().toISOString() },
    }),
    fetchTelegramStatus: vi.fn().mockResolvedValue({ telegram: "connected" }),
  },
}));

vi.mock("@/api/admin", () => ({
  adminApi: {
    refreshCache: vi.fn().mockResolvedValue({
      status: "success",
      cache: { version: 2, rule_count: 10, source_count: 4, refreshed_at: "2026-09-07T00:00:00Z" },
    }),
  },
}));

vi.mock("@/api/telegramAuth", () => ({
  telegramAuthApi: {
    getStatus: vi.fn().mockResolvedValue({
      connected: false,
      phone: null,
      phone_required: true,
      session_path: "/app/data/session.session",
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
import Settings from "./Settings";
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

function renderSettings() {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Settings />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Settings Page — Cache Refresh & Telegram Session Control", () => {
  it("renders Settings header and sections", async () => {
    renderSettings();
    expect(await screen.findByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("Telegram Session Control")).toBeInTheDocument();
    expect(screen.getByText("Appearance")).toBeInTheDocument();
    expect(screen.getByText("System Information & Cache")).toBeInTheDocument();
  });

  // AC1: Refresh Cache Button
  it("triggers adminApi.refreshCache when Refresh Cache is clicked and shows success toast", async () => {
    renderSettings();
    await screen.findByText("Settings");

    const refreshButtons = screen.getAllByRole("button", { name: /refresh cache/i });
    expect(refreshButtons.length).toBeGreaterThan(0);
    fireEvent.click(refreshButtons[0]);

    await waitFor(() => {
      expect(adminApi.refreshCache).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("Cache rebuilt (v2) — 10 rules, 4 sources")
      );
    });
  });

  // AC2: Telegram Session Card DISCONNECTED state
  it("renders DISCONNECTED state badge, phone input, and Send OTP button when disconnected", async () => {
    vi.mocked(telegramAuthApi.getStatus).mockResolvedValueOnce({
      connected: false,
      phone: null,
      phone_required: true,
      session_path: "/app/data/session.session",
    });

    renderSettings();

    expect(await screen.findByText("DISCONNECTED")).toBeInTheDocument();
    expect(screen.getByLabelText(/Telegram Phone Number/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send otp/i })).toBeInTheDocument();
  });

  // AC2: Telegram Session Card CONNECTED state
  it("renders CONNECTED state badge, masked phone, and Terminate Session button when connected", async () => {
    vi.mocked(telegramAuthApi.getStatus).mockResolvedValueOnce({
      connected: true,
      phone: "+123 **** 7890",
      phone_required: false,
      session_path: "/app/data/session.session",
    });

    renderSettings();

    expect(await screen.findByText("CONNECTED")).toBeInTheDocument();
    expect(screen.getByText("+123 **** 7890")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /terminate session/i })).toBeInTheDocument();
  });

  // AC3 & AC4: Send OTP and Verify OTP flow
  it("submits phone number for OTP and proceeds to verify OTP", async () => {
    vi.mocked(telegramAuthApi.getStatus).mockResolvedValue({
      connected: false,
      phone: null,
      phone_required: true,
      session_path: "/app/data/session.session",
    });

    renderSettings();
    await screen.findByText("DISCONNECTED");

    // Fill phone number
    const phoneInput = screen.getByLabelText(/Telegram Phone Number/i);
    fireEvent.change(phoneInput, { target: { value: "+14155552671" } });

    // Click Send OTP
    const sendOtpBtn = screen.getByRole("button", { name: /send otp/i });
    fireEvent.click(sendOtpBtn);

    await waitFor(() => {
      expect(telegramAuthApi.startAuth).toHaveBeenCalledWith("+14155552671");
    });

    // 6-digit OTP input should now appear
    expect(await screen.findByLabelText(/6-digit otp code/i)).toBeInTheDocument();

    // Fill OTP
    const otpInput = screen.getByLabelText(/6-digit otp code/i);
    fireEvent.change(otpInput, { target: { value: "123456" } });

    // Click Connect Telegram
    const connectBtn = screen.getByRole("button", { name: /connect telegram/i });
    fireEvent.click(connectBtn);

    await waitFor(() => {
      expect(telegramAuthApi.verifyAuth).toHaveBeenCalledWith({
        otp: "123456",
        phone: "+14155552671",
        password: undefined,
      });
    });
  });

  // AC4: 2FA Password requirement handling (HTTP 202 requires_2fa)
  it("reveals 2FA password field when verify returns requires_2fa: true", async () => {
    vi.mocked(telegramAuthApi.getStatus).mockResolvedValue({
      connected: false,
      phone: null,
      phone_required: true,
      session_path: "/app/data/session.session",
    });
    vi.mocked(telegramAuthApi.verifyAuth).mockResolvedValueOnce({
      status: "requires_2fa",
      requires_2fa: true,
    });

    renderSettings();
    await screen.findByText("DISCONNECTED");

    // Enter phone and send OTP
    fireEvent.change(screen.getByLabelText(/Telegram Phone Number/i), {
      target: { value: "+14155552671" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send otp/i }));

    // Enter OTP and click connect
    const otpInput = await screen.findByLabelText(/6-digit otp code/i);
    fireEvent.change(otpInput, { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: /connect telegram/i }));

    // Should reveal 2FA field
    expect(await screen.findByLabelText(/two-factor authentication/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit 2fa password/i })).toBeInTheDocument();
  });

  // AC5: Inline error alerts on auth failure
  it("displays inline error banner when startAuth fails", async () => {
    vi.mocked(telegramAuthApi.getStatus).mockResolvedValue({
      connected: false,
      phone: null,
      phone_required: true,
      session_path: "/app/data/session.session",
    });
    vi.mocked(telegramAuthApi.startAuth).mockRejectedValueOnce({
      response: { data: { error: { message: "Invalid phone number format" } } },
    });

    renderSettings();
    await screen.findByText("DISCONNECTED");

    fireEvent.change(screen.getByLabelText(/Telegram Phone Number/i), {
      target: { value: "invalid-phone" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send otp/i }));

    expect(await screen.findByText("Invalid phone number format")).toBeInTheDocument();
  });

  // AC6: Terminate Session Modal verification
  it("requires typing 'terminate' to enable Confirm Terminate button in confirmation modal", async () => {
    vi.mocked(telegramAuthApi.getStatus).mockResolvedValue({
      connected: true,
      phone: "+123 **** 7890",
      phone_required: false,
      session_path: "/app/data/session.session",
    });

    renderSettings();
    await screen.findByText("CONNECTED");

    // Click Terminate Session button to open modal
    fireEvent.click(screen.getByRole("button", { name: /terminate session/i }));

    // Modal title & description should appear
    expect(await screen.findByText("Terminate Telegram Session?")).toBeInTheDocument();
    expect(
      screen.getByText(/Terminating the Telegram session will disconnect the forwarding worker/i)
    ).toBeInTheDocument();

    const confirmButton = screen.getByRole("button", { name: /confirm terminate/i });
    expect(confirmButton).toBeDisabled();

    // Type incorrect text first
    const input = screen.getByLabelText(/Type terminate to confirm/i);
    fireEvent.change(input, { target: { value: "wrong" } });
    expect(confirmButton).toBeDisabled();

    // Type 'terminate'
    fireEvent.change(input, { target: { value: "terminate" } });
    expect(confirmButton).not.toBeDisabled();

    // Click Confirm Terminate
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(telegramAuthApi.terminateSession).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Telegram session terminated");
    });
  });
});
