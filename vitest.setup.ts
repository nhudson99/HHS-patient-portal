import { config } from '@vue/test-utils'
import { vi } from 'vitest'

// Mock global properties if needed
config.global.mocks = {
  $t: (msg: string) => msg,
}

// Silence Vue warnings
vi.stubGlobal('console', {
  ...console,
  warn: () => {},
})
