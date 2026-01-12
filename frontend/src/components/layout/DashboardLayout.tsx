import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePageTitle } from "./Sidebar"
import { useNotes, useTheme } from "@/hooks"
import { Button } from "@/components/ui/button"
import { Sun, Moon } from "lucide-react"
import { BottomTabBar, BottomSheet, FAB } from "@/components/navigation"
import { QuickCapture } from "@/components/notes/QuickCapture"

interface DashboardLayoutProps {
    children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
    const pageTitle = usePageTitle()
    const navigate = useNavigate()
    const { create } = useNotes()
    const { theme, toggleTheme } = useTheme()
    const [isMoreSheetOpen, setIsMoreSheetOpen] = useState(false)
    const [isQuickCaptureOpen, setIsQuickCaptureOpen] = useState(false)

    const handleAddNote = () => {
        setIsQuickCaptureOpen(true)
    }

    const handleQuickCaptureSubmit = async (content: string, isVoiceNote?: boolean) => {
        await create(content, { isVoiceNote: isVoiceNote || false })
        setIsQuickCaptureOpen(false)
    }

    const handleQuickCount = () => {
        navigate('/count')
    }

    return (
        <div className="flex min-h-screen flex-col bg-background text-foreground">
            {/* Header - matches background with safe area support */}
            <header
                className="fixed top-0 left-0 right-0 z-40 bg-background border-b border-border"
                style={{ paddingTop: 'env(safe-area-inset-top)' }}
            >
                <div className="flex h-14 items-center gap-4 px-4">
                    <div className="flex-1">
                        <h1 className="text-lg font-semibold font-head">
                            <span className="text-primary">Steady</span>
                            <span className="text-muted-foreground"> — </span>
                            <span className="text-foreground">{pageTitle}</span>
                        </h1>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={toggleTheme}
                        className="h-9 w-9"
                        title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
                    >
                        {theme === 'dark' ? (
                            <Sun className="h-4 w-4" />
                        ) : (
                            <Moon className="h-4 w-4" />
                        )}
                    </Button>
                </div>
            </header>

            {/* Spacer for fixed header */}
            <div
                className="flex-shrink-0"
                style={{ height: 'calc(56px + env(safe-area-inset-top))' }}
            />

            {/* Main content - with bottom padding for nav */}
            <main
                className="flex-1 p-4 lg:p-6 overflow-y-auto"
                style={{ paddingBottom: 'calc(72px + env(safe-area-inset-bottom))' }}
            >
                <div className="mx-auto max-w-6xl w-full">
                    {children}
                </div>
            </main>

            {/* Bottom Tab Navigation */}
            <BottomTabBar
                onMoreClick={() => setIsMoreSheetOpen(true)}
            />

            {/* More Menu Bottom Sheet */}
            <BottomSheet
                isOpen={isMoreSheetOpen}
                onClose={() => setIsMoreSheetOpen(false)}
            />

            {/* Floating Action Button */}
            <FAB onAddNote={handleAddNote} onQuickCount={handleQuickCount} />

            {/* Quick Capture Modal for Notes */}
            {isQuickCaptureOpen && (
                <QuickCapture
                    onSubmit={handleQuickCaptureSubmit}
                    onClose={() => setIsQuickCaptureOpen(false)}
                />
            )}
        </div>
    )
}
