import '@testing-library/jest-dom'
import { vi } from 'vitest'

vi.mock('date-fns', () => ({
  format: vi.fn((date, fmt) => {
    if (date instanceof Date) return date.toISOString()
    return new Date(date).toISOString()
  }),
}))