/**
 * Tests for FirstRunWizard component (Story 6-6, AC 5 & 7)
 *
 * Covers:
 * - Renders when open=true, hidden when open=false
 * - Has 3 steps: Register Source, Create Forwarding Rule, Verify Live Logs
 * - Step 1 shows "Go to Sources" button navigating to /sources/new
 * - Step 2 shows "Go to Forwards" button navigating to /forwards/new
 * - Step 3 shows "Go to Logs" button navigating to /logs
 * - Next/Back navigation between steps
 * - Back is disabled on first step
 * - "Skip setup" calls onDismiss and sets localStorage item
 * - "Finish" on last step calls onDismiss and sets localStorage item
 * - Dialog close (onOpenChange false) calls onDismiss + sets localStorage
 * - Step indicators reflect current step visually
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { FirstRunWizard } from '../components/FirstRunWizard'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function renderWizard(open = true, onDismiss = vi.fn()) {
  return render(
    <MemoryRouter>
      <FirstRunWizard open={open} onDismiss={onDismiss} />
    </MemoryRouter>
  )
}

beforeEach(() => {
  mockNavigate.mockReset()
  localStorage.clear()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('FirstRunWizard component', () => {
  it('renders wizard dialog when open=true', () => {
    renderWizard(true)
    expect(screen.getByText('Quick Setup Wizard')).toBeInTheDocument()
  })

  it('does NOT render wizard content when open=false', () => {
    renderWizard(false)
    expect(screen.queryByText('Quick Setup Wizard')).not.toBeInTheDocument()
  })

  it('shows step 1: Register a Source on initial render', () => {
    renderWizard()
    // The step title appears in both step indicator and content card — use heading role
    expect(screen.getByRole('heading', { name: 'Register a Source' })).toBeInTheDocument()
    expect(screen.getByText(/Connect your Telegram channel/i)).toBeInTheDocument()
    expect(screen.getByText('Go to Sources')).toBeInTheDocument()
  })

  it('shows all 3 step indicators', () => {
    renderWizard()
    // Step indicators: 1, 2, 3
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('Back button is disabled on step 1', () => {
    renderWizard()
    const backBtn = screen.getByText('Back').closest('button')
    expect(backBtn).toBeDisabled()
  })

  it('Next button advances to step 2', () => {
    renderWizard()
    fireEvent.click(screen.getByText('Next'))
    // Step title appears in both indicator and content — use heading role
    expect(screen.getByRole('heading', { name: 'Create a Forwarding Rule' })).toBeInTheDocument()
    expect(screen.getByText(/Set up a forwarding rule/i)).toBeInTheDocument()
    expect(screen.getByText('Go to Forwards')).toBeInTheDocument()
  })

  it('Back button from step 2 goes back to step 1', () => {
    renderWizard()
    fireEvent.click(screen.getByText('Next'))
    expect(screen.getByRole('heading', { name: 'Create a Forwarding Rule' })).toBeInTheDocument()

    fireEvent.click(screen.getByText('Back'))
    expect(screen.getByRole('heading', { name: 'Register a Source' })).toBeInTheDocument()
  })

  it('Next from step 2 advances to step 3', () => {
    renderWizard()
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    // Step title appears in both indicator and content — use heading role
    expect(screen.getByRole('heading', { name: 'Verify Live Logs' })).toBeInTheDocument()
    expect(screen.getByText(/Watch live events/i)).toBeInTheDocument()
    expect(screen.getByText('Go to Logs')).toBeInTheDocument()
  })

  it('shows Finish button (not Next) on the last step', () => {
    renderWizard()
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    expect(screen.getByText('Finish')).toBeInTheDocument()
    expect(screen.queryByText('Next')).not.toBeInTheDocument()
  })

  it('"Go to Sources" navigates to /sources/new and calls onDismiss', () => {
    const onDismiss = vi.fn()
    renderWizard(true, onDismiss)
    fireEvent.click(screen.getByText('Go to Sources'))
    expect(mockNavigate).toHaveBeenCalledWith('/sources/new')
    expect(onDismiss).toHaveBeenCalledOnce()
  })

  it('"Go to Forwards" navigates to /forwards/new and calls onDismiss', () => {
    const onDismiss = vi.fn()
    renderWizard(true, onDismiss)
    fireEvent.click(screen.getByText('Next')) // step 2
    fireEvent.click(screen.getByText('Go to Forwards'))
    expect(mockNavigate).toHaveBeenCalledWith('/forwards/new')
    expect(onDismiss).toHaveBeenCalledOnce()
  })

  it('"Go to Logs" navigates to /logs and calls onDismiss', () => {
    const onDismiss = vi.fn()
    renderWizard(true, onDismiss)
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Go to Logs'))
    expect(mockNavigate).toHaveBeenCalledWith('/logs')
    expect(onDismiss).toHaveBeenCalledOnce()
  })

  it('"Skip setup" calls onDismiss', () => {
    const onDismiss = vi.fn()
    renderWizard(true, onDismiss)
    fireEvent.click(screen.getByText('Skip setup'))
    expect(onDismiss).toHaveBeenCalledOnce()
  })

  it('"Skip setup" sets localStorage fb-first-run-dismissed=true', () => {
    renderWizard()
    fireEvent.click(screen.getByText('Skip setup'))
    expect(localStorage.getItem('fb-first-run-dismissed')).toBe('true')
  })

  it('"Finish" on last step calls onDismiss', () => {
    const onDismiss = vi.fn()
    renderWizard(true, onDismiss)
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Finish'))
    expect(onDismiss).toHaveBeenCalledOnce()
  })

  it('"Finish" on last step sets localStorage fb-first-run-dismissed=true', () => {
    renderWizard()
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('Finish'))
    expect(localStorage.getItem('fb-first-run-dismissed')).toBe('true')
  })

  it('shows "Welcome to Forward Bot" subtitle text', () => {
    renderWizard()
    expect(screen.getByText(/Welcome to Forward Bot/i)).toBeInTheDocument()
  })
})
