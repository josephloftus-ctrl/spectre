/**
 * Tests for the KPIGrid dashboard component.
 *
 * Verifies that KPI cards display correct values and formatting,
 * including currency abbreviations and conditional styling.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KPIGrid } from '@/components/dashboard/KPIGrid'

describe('KPIGrid', () => {
  it('renders all three KPI cards', () => {
    render(<KPIGrid totalSites={5} totalIssues={3} totalValue={10000} />)

    expect(screen.getByText('Active Sites')).toBeInTheDocument()
    expect(screen.getByText('Issues Found')).toBeInTheDocument()
    expect(screen.getByText('Total Value')).toBeInTheDocument()
  })

  it('displays correct site count', () => {
    render(<KPIGrid totalSites={12} totalIssues={0} totalValue={0} />)
    expect(screen.getByText('12')).toBeInTheDocument()
  })

  it('displays correct issue count', () => {
    render(<KPIGrid totalSites={5} totalIssues={7} totalValue={0} />)
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('formats value in thousands as $XK', () => {
    render(<KPIGrid totalSites={1} totalIssues={0} totalValue={25000} />)
    expect(screen.getByText('$25K')).toBeInTheDocument()
  })

  it('formats value in millions as $X.XM', () => {
    render(<KPIGrid totalSites={1} totalIssues={0} totalValue={1500000} />)
    expect(screen.getByText('$1.5M')).toBeInTheDocument()
  })

  it('formats small values with dollar sign', () => {
    render(<KPIGrid totalSites={1} totalIssues={0} totalValue={500} />)
    expect(screen.getByText('$500')).toBeInTheDocument()
  })

  it('shows zero values correctly', () => {
    render(<KPIGrid totalSites={0} totalIssues={0} totalValue={0} />)
    // totalSites and totalIssues both show 0
    const zeros = screen.getAllByText('0')
    expect(zeros.length).toBe(2)
    expect(screen.getByText('$0')).toBeInTheDocument()
  })
})
