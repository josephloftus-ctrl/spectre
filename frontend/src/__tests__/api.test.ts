/**
 * Tests for API client helper functions.
 *
 * These test pure utility functions exported from api.ts
 * without making any actual HTTP requests.
 */
import { describe, it, expect } from 'vitest'
import { formatSiteName } from '@/lib/api'

describe('formatSiteName', () => {
  it('converts underscored site ID to display name', () => {
    expect(formatSiteName('pseg_nhq')).toBe('PSEG NHQ')
  })

  it('keeps known abbreviations uppercase', () => {
    expect(formatSiteName('pseg_hq')).toBe('PSEG HQ')
  })

  it('title-cases regular words', () => {
    expect(formatSiteName('lockheed_martin_bldg_100')).toBe('Lockheed Martin Bldg 100')
  })

  it('handles single word', () => {
    expect(formatSiteName('salem')).toBe('Salem')
  })

  it('handles single abbreviation', () => {
    expect(formatSiteName('nhq')).toBe('NHQ')
  })

  it('handles multiple abbreviations in a row', () => {
    expect(formatSiteName('pseg_nhq_nj')).toBe('PSEG NHQ NJ')
  })
})
