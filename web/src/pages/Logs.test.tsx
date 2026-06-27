/**
 * Tests for Logs page (Story 6-6, AC 1-4)
 *
 * Covers:
 * AC1 — Historical batch loading + SSE live tail + auto-scroll
 * AC2 — SSE disconnect banner & reconnect
 * AC3 — Filter chips (severity) + URL persistence + Clear filters
 * AC4 — Correlation ID tracing: filter by ID, Jump to rule link
 */

import { render, screen, fireEvent, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import type { LogEntry } from '@/types/ui'

// ---------------------------------------------------------------------------
// Mock modules before importing the component
// ---------------------------------------------------------------------------

vi.mock('@/api/logs', () => ({
  SSE_STREAM_URL: '/api/v1/logs/stream',
  logsApi: {
    fetchRecent: vi.fn().mockResolvedValue({ items: [] }),
    searchLogs: vi.fn().mockResolvedValue({ items: [] }),
  },
}))

vi.mock('@/api/health', () => ({
  healthApi: {
    fetchTelegramStatus: vi.fn().mockResolvedValue({ telegram: 'connected' }),
  },
}))

vi.mock('@/hooks/useSseLog', () => ({
  useSseLog: vi.fn().mockReturnValue({
    entries: [],
    isConnected: true,
    isError: false,
  }),
}))

// Import after mocks are set up
import Logs from '../pages/Logs'
import { logsApi } from '@/api/logs'
import { useSseLog } from '@/hooks/useSseLog'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeEntry(overrides: Partial<LogEntry> = {}): LogEntry {
  return {
    event: 'forward_succeeded',
    level: 'info',
    timestamp: new Date().toISOString(),
    ...overrides,
  }
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
}

function renderLogs(initialPath = '/logs') {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/logs" element={<Logs />} />
          <Route path="*" element={<div>Other page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

const mockLogsApi = logsApi as { fetchRecent: Mock; searchLogs: Mock }
const mockUseSseLog = useSseLog as Mock

beforeEach(() => {
  vi.clearAllMocks()
  mockLogsApi.fetchRecent.mockResolvedValue({ items: [] })
  mockUseSseLog.mockReturnValue({ entries: [], isConnected: true, isError: false })
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Logs page', () => {
  // -------------------------------------------------------------------------
  // AC1: Historical batch + SSE live tail
  // -------------------------------------------------------------------------

  it('renders the System Logs heading', async () => {
    renderLogs()
    expect(await screen.findByText('System Logs')).toBeInTheDocument()
  })

  it('calls logsApi.fetchRecent(200) on mount', async () => {
    renderLogs()
    await screen.findByText('System Logs')
    expect(mockLogsApi.fetchRecent).toHaveBeenCalledWith(200)
  })

  it('shows "Live Feed" status badge when SSE is connected', async () => {
    mockUseSseLog.mockReturnValue({ entries: [], isConnected: true, isError: false })
    renderLogs()
    expect(await screen.findByText('Live Feed')).toBeInTheDocument()
  })

  it('shows "Disconnected" status badge when SSE is not connected', async () => {
    mockUseSseLog.mockReturnValue({ entries: [], isConnected: false, isError: false })
    renderLogs()
    expect(await screen.findByText('Disconnected')).toBeInTheDocument()
  })

  it('renders historical log entries as LogRow components', async () => {
    const entries = [
      makeEntry({ event: 'forward_succeeded', timestamp: '2025-01-01T10:00:00.000Z' }),
      makeEntry({ event: 'pipeline_blocked', timestamp: '2025-01-01T11:00:00.000Z' }),
    ]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs()

    expect(await screen.findByText('Forward Succeeded')).toBeInTheDocument()
    expect(await screen.findByText('Pipeline Blocked')).toBeInTheDocument()
  })

  it('renders SSE (live) entries merged with historical entries', async () => {
    const historical = [makeEntry({ event: 'forward_succeeded', timestamp: '2025-01-01T10:00:00.000Z' })]
    const live = [makeEntry({ event: 'pipeline_blocked', timestamp: '2025-01-01T12:00:00.000Z' })]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: historical })
    mockUseSseLog.mockReturnValue({ entries: live, isConnected: true, isError: false })

    renderLogs()

    expect(await screen.findByText('Forward Succeeded')).toBeInTheDocument()
    expect(await screen.findByText('Pipeline Blocked')).toBeInTheDocument()
  })

  it('shows loading spinner while historical data is loading', () => {
    // fetchRecent never resolves for this test
    mockLogsApi.fetchRecent.mockReturnValue(new Promise(() => {}))
    renderLogs()
    expect(screen.getByText('Loading system logs...')).toBeInTheDocument()
  })

  it('shows error state when historical batch fails', async () => {
    mockLogsApi.fetchRecent.mockRejectedValue(new Error('Network error'))
    renderLogs()
    expect(await screen.findByText('Failed to Load Logs')).toBeInTheDocument()
    expect(screen.getByText('Retry Load')).toBeInTheDocument()
  })

  it('shows empty state when no entries and no filters', async () => {
    mockLogsApi.fetchRecent.mockResolvedValue({ items: [] })
    mockUseSseLog.mockReturnValue({ entries: [], isConnected: true, isError: false })
    renderLogs()
    expect(await screen.findByText('No Logs Found')).toBeInTheDocument()
    expect(screen.getByText(/No activities registered/i)).toBeInTheDocument()
  })

  // -------------------------------------------------------------------------
  // AC1: Auto-scroll controls
  // -------------------------------------------------------------------------

  it('renders "Pause Scroll" button when entries are present', async () => {
    const entries = [makeEntry()]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs()
    expect(await screen.findByText('Pause Scroll')).toBeInTheDocument()
  })

  it('toggles auto-scroll state: Pause → Auto Scroll on click', async () => {
    const entries = [makeEntry()]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs()

    const pauseBtn = await screen.findByText('Pause Scroll')
    fireEvent.click(pauseBtn)

    expect(screen.getByText('Auto Scroll')).toBeInTheDocument()
    expect(screen.getByText('Tail Mode Paused')).toBeInTheDocument()
  })

  it('shows "Tail Mode Enabled" label when auto-scroll is active', async () => {
    const entries = [makeEntry()]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs()
    expect(await screen.findByText('Tail Mode Enabled')).toBeInTheDocument()
  })

  // -------------------------------------------------------------------------
  // AC2: SSE Disconnect Banner
  // -------------------------------------------------------------------------

  it('shows DegradedBanner when SSE isError=true', async () => {
    mockLogsApi.fetchRecent.mockResolvedValue({ items: [] })
    mockUseSseLog.mockReturnValue({ entries: [], isConnected: false, isError: true })
    renderLogs()
    expect(await screen.findByText(/Live log stream disconnected/i)).toBeInTheDocument()
  })

  it('does NOT show DegradedBanner when SSE isError=false', async () => {
    mockLogsApi.fetchRecent.mockResolvedValue({ items: [] })
    mockUseSseLog.mockReturnValue({ entries: [], isConnected: true, isError: false })
    renderLogs()
    await screen.findByText('System Logs')
    expect(screen.queryByText(/Live log stream disconnected/i)).not.toBeInTheDocument()
  })

  // -------------------------------------------------------------------------
  // AC3: Severity filter chips + URL persistence
  // -------------------------------------------------------------------------

  it('renders all 4 severity filter chips', async () => {
    renderLogs()
    await screen.findByText('System Logs')
    expect(screen.getByRole('button', { name: /^info$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^warning$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^error$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^success$/i })).toBeInTheDocument()
  })

  it('renders Trace ID input field', async () => {
    renderLogs()
    await screen.findByText('System Logs')
    expect(screen.getByPlaceholderText('correlation-id')).toBeInTheDocument()
  })

  it('filters entries by severity chip (error only)', async () => {
    const entries = [
      makeEntry({ event: 'forward_succeeded', level: 'info', timestamp: '2025-01-01T10:00:00.000Z' }),
      makeEntry({ event: 'forward_failed', level: 'error', timestamp: '2025-01-01T11:00:00.000Z' }),
    ]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs()

    await screen.findByText('Forward Succeeded')

    // Click error chip
    fireEvent.click(screen.getByRole('button', { name: /^error$/i }))

    // Only error entry should be visible now
    expect(screen.queryByText('Forward Succeeded')).not.toBeInTheDocument()
    expect(screen.getByText('Forward Failed')).toBeInTheDocument()
  })

  it('shows "Clear active filters" button when severity filter is active', async () => {
    mockLogsApi.fetchRecent.mockResolvedValue({ items: [makeEntry()] })
    renderLogs()
    await screen.findByText('Forward Succeeded')

    fireEvent.click(screen.getByRole('button', { name: /^error$/i }))
    expect(screen.getByText('Clear active filters')).toBeInTheDocument()
  })

  it('clearing filters resets visible entries', async () => {
    const entries = [
      makeEntry({ event: 'forward_succeeded', level: 'info', timestamp: '2025-01-01T10:00:00.000Z' }),
      makeEntry({ event: 'forward_failed', level: 'error', timestamp: '2025-01-01T11:00:00.000Z' }),
    ]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs()

    await screen.findByText('Forward Succeeded')

    // Filter to error only
    fireEvent.click(screen.getByRole('button', { name: /^error$/i }))
    expect(screen.queryByText('Forward Succeeded')).not.toBeInTheDocument()

    // Clear filters
    fireEvent.click(screen.getByText('Clear active filters'))
    expect(await screen.findByText('Forward Succeeded')).toBeInTheDocument()
  })

  it('shows "No Logs Found" with filter-specific message when filter yields no results', async () => {
    const entries = [makeEntry({ event: 'forward_succeeded', level: 'info', timestamp: '2025-01-01T10:00:00.000Z' })]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs()

    await screen.findByText('Forward Succeeded')

    // Filter to error — no error entries exist
    fireEvent.click(screen.getByRole('button', { name: /^error$/i }))

    expect(await screen.findByText('No Logs Found')).toBeInTheDocument()
    expect(screen.getByText(/No log entries match the current filters/i)).toBeInTheDocument()
    expect(screen.getByText('Clear all filters')).toBeInTheDocument()
  })

  it('pre-selects severity filter from URL query param', async () => {
    const entries = [
      makeEntry({ event: 'forward_succeeded', level: 'info', timestamp: '2025-01-01T10:00:00.000Z' }),
      makeEntry({ event: 'forward_failed', level: 'error', timestamp: '2025-01-01T11:00:00.000Z' }),
    ]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs('/logs?severity=error')

    await screen.findByText('Forward Failed')
    expect(screen.queryByText('Forward Succeeded')).not.toBeInTheDocument()
  })

  it('shows entry count when filters active', async () => {
    const entries = [
      makeEntry({ event: 'forward_succeeded', level: 'info', timestamp: '2025-01-01T10:00:00.000Z' }),
      makeEntry({ event: 'forward_failed', level: 'error', timestamp: '2025-01-01T11:00:00.000Z' }),
    ]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs()

    await screen.findByText('Forward Succeeded')
    fireEvent.click(screen.getByRole('button', { name: /^error$/i }))

    expect(await screen.findByText(/Showing 1 of 2 buffered log events/)).toBeInTheDocument()
  })

  // -------------------------------------------------------------------------
  // AC4: Correlation ID tracing
  // -------------------------------------------------------------------------

  it('filters by correlation_id when typed in Trace ID input', async () => {
    const entries = [
      makeEntry({ event: 'forward_succeeded', level: 'info', timestamp: '2025-01-01T10:00:00.000Z', correlation_id: 'trace-aaa' }),
      makeEntry({ event: 'pipeline_blocked', level: 'info', timestamp: '2025-01-01T11:00:00.000Z', correlation_id: 'trace-bbb' }),
    ]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs()

    await screen.findByText('Forward Succeeded')

    // Type correlation ID in Trace ID field
    fireEvent.change(screen.getByPlaceholderText('correlation-id'), {
      target: { value: 'trace-aaa' },
    })

    // Only matching entry should show
    expect(screen.getByText('Forward Succeeded')).toBeInTheDocument()
    expect(screen.queryByText('Pipeline Blocked')).not.toBeInTheDocument()
  })

  it('shows clear (×) button inside Trace ID input when value is typed', async () => {
    renderLogs()
    await screen.findByText('System Logs')

    const input = screen.getByPlaceholderText('correlation-id')
    fireEvent.change(input, { target: { value: 'abc123' } })

    // The X button inside the input
    const clearBtn = input.parentElement?.querySelector('button')
    expect(clearBtn).toBeInTheDocument()
  })

  it('shows "Jump to forwarding rule →" link in filter bar when correlation_id entry has rule_id', async () => {
    const entries = [
      makeEntry({
        event: 'forward_succeeded',
        level: 'info',
        timestamp: '2025-01-01T10:00:00.000Z',
        correlation_id: 'corr-xyz',
        rule_id: 'rule-42',
      }),
    ]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs('/logs?correlation_id=corr-xyz')

    expect(await screen.findByText('Jump to forwarding rule →')).toBeInTheDocument()
    const link = screen.getByText('Jump to forwarding rule →').closest('a')
    expect(link).toHaveAttribute('href', '/forwards/rule-42/edit')
  })

  it('pre-selects correlation_id filter from URL query param', async () => {
    const entries = [
      makeEntry({ event: 'forward_succeeded', level: 'info', timestamp: '2025-01-01T10:00:00.000Z', correlation_id: 'corr-abc' }),
      makeEntry({ event: 'pipeline_blocked', level: 'info', timestamp: '2025-01-01T11:00:00.000Z', correlation_id: 'corr-def' }),
    ]
    mockLogsApi.fetchRecent.mockResolvedValue({ items: entries })
    renderLogs('/logs?correlation_id=corr-abc')

    await screen.findByText('Forward Succeeded')
    expect(screen.queryByText('Pipeline Blocked')).not.toBeInTheDocument()
  })

  it('shows "Buffer limit: 1000 items" in footer', async () => {
    mockLogsApi.fetchRecent.mockResolvedValue({ items: [makeEntry()] })
    renderLogs()
    expect(await screen.findByText('Buffer limit: 1000 items')).toBeInTheDocument()
  })
})
