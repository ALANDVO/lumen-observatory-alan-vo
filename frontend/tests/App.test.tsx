import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import App from '../src/App'
import { api } from '../src/api/client'

vi.mock('../src/api/client', () => ({
  api: {
    healthCheck: vi.fn(),
    listActors: vi.fn(),
  },
}))

const mockActors = [
  {
    actor_uid: 'test-1',
    actor_name: 'Test Actor 1',
    actor_atespace: 'default',
    actor_template_namespace: 'ns1',
    actor_template_name: 'tmpl1',
    container_name: 'main',
    state: 'RUNNING' as const,
    snapshot_scope: 'data' as const,
    node_name: 'node-1',
    worker_pod: 'pod-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T01:00:00Z',
    last_snapshot_at: null,
    tags: null,
  },
  {
    actor_uid: 'test-2',
    actor_name: 'Test Actor 2',
    actor_atespace: 'default',
    actor_template_namespace: 'ns1',
    actor_template_name: 'tmpl2',
    container_name: 'main',
    state: 'SUSPENDED' as const,
    snapshot_scope: 'full' as const,
    node_name: null,
    worker_pod: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T02:00:00Z',
    last_snapshot_at: '2024-01-01T01:30:00Z',
    tags: 'v1',
  },
]

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders navigation', () => {
    render(<App />, { wrapper: BrowserRouter })
    expect(screen.getByRole('tab', { name: 'Actors' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Metrics' })).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    api.listActors.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 20 })
    render(<App />, { wrapper: BrowserRouter })
    expect(screen.getByRole('heading', { name: 'Actors' })).toBeInTheDocument()
  })
})

describe('ActorTable', () => {
  it('renders actor rows', async () => {
    api.listActors.mockResolvedValue({ items: mockActors, total: 2, skip: 0, limit: 20 })
    api.healthCheck.mockResolvedValue({ status: 'healthy' })

    render(<App />, { wrapper: BrowserRouter })

    await waitFor(() => {
      expect(screen.getByText('Test Actor 1')).toBeInTheDocument()
      expect(screen.getByText('Test Actor 2')).toBeInTheDocument()
    })
  })

  it('shows empty state when no actors', async () => {
    api.listActors.mockResolvedValue({ items: [], total: 0, skip: 0, limit: 20 })
    api.healthCheck.mockResolvedValue({ status: 'healthy' })

    render(<App />, { wrapper: BrowserRouter })

    await waitFor(() => {
      expect(screen.getByText('No actors found')).toBeInTheDocument()
    })
  })
})