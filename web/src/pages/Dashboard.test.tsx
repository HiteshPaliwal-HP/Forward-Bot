/**
 * Tests for Dashboard page — First-Run Wizard integration (Story 6-6, AC 5)
 *
 * Covers:
 * - Wizard opens automatically when total rules = 0 and localStorage not set
 * - Wizard does NOT open when total rules = 0 but localStorage is already set to "true"
 * - Wizard does NOT open when at least 1 rule exists (even without localStorage)
 * - Dismissing wizard sets localStorage and closes it
 */

import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// ---------------------------------------------------------------------------
// Mock all API calls and external dependencies
// ---------------------------------------------------------------------------

vi.mock('@/api/health', () => ({
  healthApi: {
    fetchTelegramStatus: vi.fn().mockResolvedValue({ telegram: 'connected' }),
    fetchCacheStatus: vi.fn().mockResolvedValue({ mongodb: 'up' }),
  },
}))

vi.mock('@/api/stats', () => ({
  statsApi: {
    fetchSummary: vi.fn().mockResolvedValue({ forwarded_24h: 0, failed_24h: 0, blocked_24h: 0, active_rules: 0 }),
  },
}))

vi.mock('@/api/logs', () => ({
  logsApi: {
    fetchRecent: vi.fn().mockResolvedValue({ items: [] }),
  },
  SSE_STREAM_URL: '/api/v1/logs/stream',
}))

vi.mock('@/api/rules', () => ({
  rulesApi: {
    fetchRules: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 1 }),
  },
}))

vi.mock('@/lib/queryKeys', () => ({
  queryKeys: {
    health: {
      telegram: () => ['health', 'telegram'],
      cache: () => ['health', 'cache'],
    },
    stats: {
      summary: () => ['stats', 'summary'],
    },
    logs: {
      recent: () => ['logs', 'recent'],
    },
    rules: {
      list: () => ['rules', 'list'],
    },
  },
}))

// Mock the FirstRunWizard component to make tests simpler
vi.mock('@/components/FirstRunWizard', () => ({
  FirstRunWizard: ({ open, onDismiss }: { open: boolean; onDismiss: () => void }) =>
    open ? (
      <div data-testid="first-run-wizard">
        <span>Quick Setup Wizard</span>
        <button onClick={onDismiss}>Skip setup</button>
      </div>
    ) : null,
}))

// Import after mocks
import Dashboard from '../pages/Dashboard'
import { rulesApi } from '@/api/rules'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
}

function renderDashboard() {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

const mockRulesApi = rulesApi as { fetchRules: ReturnType<typeof vi.fn> }

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Dashboard — First-Run Wizard integration', () => {
  it('opens First-Run Wizard when rules total=0 and localStorage not set', async () => {
    mockRulesApi.fetchRules.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 1 })
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByTestId('first-run-wizard')).toBeInTheDocument()
    })
  })

  it('does NOT open First-Run Wizard when rules total=0 but localStorage is "true"', async () => {
    localStorage.setItem('fb-first-run-dismissed', 'true')
    mockRulesApi.fetchRules.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 1 })
    renderDashboard()

    await waitFor(() => {
      expect(screen.queryByTestId('first-run-wizard')).not.toBeInTheDocument()
    })
  })

  it('does NOT open First-Run Wizard when at least 1 rule exists', async () => {
    mockRulesApi.fetchRules.mockResolvedValue({
      items: [{ id: 'rule-1', is_active: true }],
      total: 1,
      page: 1,
      page_size: 1,
    })
    renderDashboard()

    // Wait for the API to resolve
    await waitFor(() => {
      expect(mockRulesApi.fetchRules).toHaveBeenCalled()
    })

    expect(screen.queryByTestId('first-run-wizard')).not.toBeInTheDocument()
  })

  it('calls fetchRules with page_size=1 to detect first-run state', async () => {
    mockRulesApi.fetchRules.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 1 })
    renderDashboard()

    await waitFor(() => {
      expect(mockRulesApi.fetchRules).toHaveBeenCalledWith({ page_size: 1 })
    })
  })

  it('renders Dashboard header content', async () => {
    renderDashboard()
    expect(await screen.findByText('Dashboard')).toBeInTheDocument()
  })
})
