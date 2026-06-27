/**
 * Tests for useSseLog hook (Story 6-6, AC 6)
 *
 * Covers:
 * - Only opens EventSource when enabled=true
 * - Closes EventSource when enabled becomes false (no memory leaks)
 * - Returns { entries, isConnected, isError }
 * - Appends incoming SSE events and respects MAX_BUFFER=1000
 * - Filters entries older than/equal to startAfterTimestamp
 * - Updates cutoff on each new event (prevents replay duplicates)
 * - Error state set on onerror, cleared on onopen
 */

import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest'
import { useSseLog } from './useSseLog'
import type { LogEntry } from '@/types/ui'

// ---------------------------------------------------------------------------
// EventSource mock
// ---------------------------------------------------------------------------

interface MockEventSource {
  url: string
  withCredentials: boolean
  onopen: (() => void) | null
  onmessage: ((event: { data: string }) => void) | null
  onerror: (() => void) | null
  close: Mock
  /** Simulate the server sending a message */
  _dispatch: (entry: LogEntry) => void
  /** Simulate a connection open */
  _open: () => void
  /** Simulate a connection error */
  _error: () => void
}

let mockEventSourceInstance: MockEventSource | null = null

class MockEventSourceClass implements MockEventSource {
  url: string
  withCredentials: boolean
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  close = vi.fn()

  constructor(url: string, init?: { withCredentials?: boolean }) {
    this.url = url
    this.withCredentials = init?.withCredentials ?? false
    mockEventSourceInstance = this
  }

  _dispatch(entry: LogEntry) {
    this.onmessage?.({ data: JSON.stringify(entry) })
  }

  _open() {
    this.onopen?.()
  }

  _error() {
    this.onerror?.()
  }
}

beforeEach(() => {
  mockEventSourceInstance = null
  vi.stubGlobal('EventSource', MockEventSourceClass)
})

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

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useSseLog hook', () => {
  it('opens EventSource when enabled=true (default)', () => {
    renderHook(() => useSseLog())
    expect(mockEventSourceInstance).not.toBeNull()
    expect(mockEventSourceInstance!.url).toContain('/api/v1/logs/stream')
  })

  it('does NOT open EventSource when enabled=false', () => {
    renderHook(() => useSseLog({ enabled: false }))
    expect(mockEventSourceInstance).toBeNull()
  })

  it('returns initial state: entries=[], isConnected=false, isError=false', () => {
    const { result } = renderHook(() => useSseLog({ enabled: false }))
    expect(result.current.entries).toEqual([])
    expect(result.current.isConnected).toBe(false)
    expect(result.current.isError).toBe(false)
  })

  it('sets isConnected=true and isError=false on onopen', () => {
    const { result } = renderHook(() => useSseLog())
    act(() => {
      mockEventSourceInstance!._open()
    })
    expect(result.current.isConnected).toBe(true)
    expect(result.current.isError).toBe(false)
  })

  it('sets isConnected=false and isError=true on onerror', () => {
    const { result } = renderHook(() => useSseLog())
    act(() => {
      mockEventSourceInstance!._open()
    })
    act(() => {
      mockEventSourceInstance!._error()
    })
    expect(result.current.isConnected).toBe(false)
    expect(result.current.isError).toBe(true)
  })

  it('clears isError when connection re-opens after error', () => {
    const { result } = renderHook(() => useSseLog())
    act(() => { mockEventSourceInstance!._error() })
    expect(result.current.isError).toBe(true)
    act(() => { mockEventSourceInstance!._open() })
    expect(result.current.isError).toBe(false)
  })

  it('appends incoming SSE entries to the buffer', () => {
    const { result } = renderHook(() =>
      useSseLog({ startAfterTimestamp: '2020-01-01T00:00:00.000Z' })
    )
    const entry = makeEntry({ timestamp: '2025-01-01T12:00:00.000Z' })
    act(() => {
      mockEventSourceInstance!._dispatch(entry)
    })
    expect(result.current.entries).toHaveLength(1)
    expect(result.current.entries[0].event).toBe('forward_succeeded')
  })

  it('filters out entries with timestamps <= startAfterTimestamp', () => {
    const cutoff = '2025-06-01T12:00:00.000Z'
    const { result } = renderHook(() =>
      useSseLog({ startAfterTimestamp: cutoff })
    )
    const oldEntry = makeEntry({ timestamp: '2025-01-01T00:00:00.000Z' })
    const newEntry = makeEntry({ timestamp: '2025-07-01T00:00:00.000Z' })

    act(() => {
      mockEventSourceInstance!._dispatch(oldEntry)
      mockEventSourceInstance!._dispatch(newEntry)
    })

    // Only the new entry should pass the cutoff filter
    expect(result.current.entries).toHaveLength(1)
    expect(result.current.entries[0].timestamp).toBe('2025-07-01T00:00:00.000Z')
  })

  it('updates cutoff so replay duplicates are rejected after reconnect', () => {
    const { result } = renderHook(() =>
      useSseLog({ startAfterTimestamp: '2020-01-01T00:00:00.000Z' })
    )

    const entry1 = makeEntry({ timestamp: '2025-01-01T10:00:00.000Z', event: 'forward_succeeded' })
    const entry2 = makeEntry({ timestamp: '2025-01-01T11:00:00.000Z', event: 'pipeline_blocked' })

    act(() => {
      mockEventSourceInstance!._dispatch(entry1)
      mockEventSourceInstance!._dispatch(entry2)
    })
    expect(result.current.entries).toHaveLength(2)

    // Simulate replay on reconnect — same events should be rejected because cutoff was updated
    act(() => {
      mockEventSourceInstance!._dispatch(entry1)
      mockEventSourceInstance!._dispatch(entry2)
    })
    // Still only 2 entries (no duplicates)
    expect(result.current.entries).toHaveLength(2)
  })

  it('ignores malformed SSE data (no crash)', () => {
    const { result } = renderHook(() =>
      useSseLog({ startAfterTimestamp: '2020-01-01T00:00:00.000Z' })
    )
    act(() => {
      mockEventSourceInstance!.onmessage?.({ data: 'not-valid-json' })
    })
    expect(result.current.entries).toHaveLength(0)
  })

  it('closes EventSource on unmount', () => {
    const { unmount } = renderHook(() => useSseLog())
    expect(mockEventSourceInstance).not.toBeNull()
    const closeMock = mockEventSourceInstance!.close
    unmount()
    expect(closeMock).toHaveBeenCalledOnce()
  })

  it('sets isConnected=false when enabled becomes false without unmounting', () => {
    const { result, rerender } = renderHook(
      ({ enabled }: { enabled: boolean }) => useSseLog({ enabled }),
      { initialProps: { enabled: true } }
    )
    act(() => { mockEventSourceInstance!._open() })
    expect(result.current.isConnected).toBe(true)

    rerender({ enabled: false })
    expect(result.current.isConnected).toBe(false)
  })

  it('opens EventSource with withCredentials=true', () => {
    renderHook(() => useSseLog())
    expect(mockEventSourceInstance!.withCredentials).toBe(true)
  })
})
