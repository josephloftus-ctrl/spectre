import { useState, useCallback, useEffect, useRef } from 'react'
import { db } from '@/lib/db'

// File System Access API types
interface FileSystemDirectoryHandle {
  kind: 'directory'
  name: string
  values(): AsyncIterable<FileSystemHandle>
  getFileHandle(name: string): Promise<FileSystemFileHandle>
  queryPermission(descriptor?: { mode: 'read' | 'readwrite' }): Promise<PermissionState>
  requestPermission(descriptor?: { mode: 'read' | 'readwrite' }): Promise<PermissionState>
}

interface FileSystemFileHandle {
  kind: 'file'
  name: string
  getFile(): Promise<File>
}

type FileSystemHandle = FileSystemDirectoryHandle | FileSystemFileHandle

declare global {
  interface Window {
    showDirectoryPicker?: () => Promise<FileSystemDirectoryHandle>
  }
}

// Store handle in IndexedDB
const HANDLE_KEY = 'folder_handle'
const AUTO_SCAN_INTERVAL = 30000 // 30 seconds

export function useFolderPicker(onNewFiles?: (files: File[]) => void) {
  const [isSupported] = useState(() => 'showDirectoryPicker' in window)
  const [folderName, setFolderName] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [autoScanEnabled, setAutoScanEnabled] = useState(true)
  const [handleRef, setHandleRef] = useState<FileSystemDirectoryHandle | null>(null)
  const seenFilesRef = useRef<Set<string>>(new Set())
  const onNewFilesRef = useRef(onNewFiles)

  // Keep callback ref updated
  useEffect(() => {
    onNewFilesRef.current = onNewFiles
  }, [onNewFiles])

  // Try to restore saved handle on mount
  useEffect(() => {
    if (!isSupported) return

    const restore = async () => {
      try {
        // Check if we have a stored handle
        const stored = await (db as any).table('_folderHandles')?.get(HANDLE_KEY)
        if (stored?.handle) {
          // Verify we still have permission
          const permission = await stored.handle.queryPermission({ mode: 'read' })
          if (permission === 'granted') {
            setHandleRef(stored.handle)
            setFolderName(stored.handle.name)
            setIsConnected(true)
          }
        }
      } catch (e) {
        // Handle table might not exist yet, or permission denied
        console.log('No saved folder handle or permission denied')
      }
    }
    restore()
  }, [isSupported])

  const pickFolder = useCallback(async () => {
    if (!window.showDirectoryPicker) {
      throw new Error('File System Access API not supported')
    }

    try {
      const handle = await window.showDirectoryPicker()

      // Request read permission
      const permission = await handle.requestPermission({ mode: 'read' })
      if (permission !== 'granted') {
        throw new Error('Permission denied')
      }

      // Store handle for later
      try {
        // Create table if it doesn't exist
        if (!(db as any).table('_folderHandles')) {
          await db.version(db.verno + 1).stores({
            _folderHandles: 'id'
          })
        }
        await (db as any).table('_folderHandles')?.put({
          id: HANDLE_KEY,
          handle,
          path: handle.name
        })
      } catch (e) {
        console.warn('Could not persist folder handle:', e)
      }

      setHandleRef(handle)
      setFolderName(handle.name)
      setIsConnected(true)

      return handle
    } catch (e) {
      if ((e as Error).name === 'AbortError') {
        // User cancelled
        return null
      }
      throw e
    }
  }, [])

  const disconnect = useCallback(async () => {
    setHandleRef(null)
    setFolderName(null)
    setIsConnected(false)

    try {
      await (db as any).table('_folderHandles')?.delete(HANDLE_KEY)
    } catch (e) {
      // Ignore
    }
  }, [])

  const scanFolder = useCallback(async (onlyNew: boolean = false): Promise<File[]> => {
    if (!handleRef) {
      throw new Error('No folder connected')
    }

    // Re-verify permission
    const permission = await handleRef.queryPermission({ mode: 'read' })
    if (permission !== 'granted') {
      const newPermission = await handleRef.requestPermission({ mode: 'read' })
      if (newPermission !== 'granted') {
        throw new Error('Permission denied')
      }
    }

    setIsScanning(true)

    try {
      const files: File[] = []
      const newFiles: File[] = []
      const validExtensions = ['.xlsx', '.xls', '.pdf', '.csv']

      for await (const entry of handleRef.values()) {
        if (entry.kind === 'file') {
          const ext = '.' + entry.name.split('.').pop()?.toLowerCase()
          if (validExtensions.includes(ext)) {
            const file = await (entry as FileSystemFileHandle).getFile()
            const fileKey = `${file.name}_${file.lastModified}`

            if (!seenFilesRef.current.has(fileKey)) {
              seenFilesRef.current.add(fileKey)
              newFiles.push(file)
            }
            files.push(file)
          }
        }
      }

      // Sort by modification time, newest first
      files.sort((a, b) => b.lastModified - a.lastModified)
      newFiles.sort((a, b) => b.lastModified - a.lastModified)

      // Notify about new files if callback provided
      if (newFiles.length > 0 && onNewFilesRef.current) {
        onNewFilesRef.current(newFiles)
      }

      return onlyNew ? newFiles : files
    } finally {
      setIsScanning(false)
    }
  }, [handleRef])

  // Auto-scan interval when connected
  useEffect(() => {
    if (!isConnected || !handleRef || !autoScanEnabled) return

    const interval = setInterval(() => {
      scanFolder(true).catch(console.error)
    }, AUTO_SCAN_INTERVAL)

    // Initial scan for new files
    scanFolder(true).catch(console.error)

    return () => clearInterval(interval)
  }, [isConnected, handleRef, autoScanEnabled, scanFolder])

  const toggleAutoScan = useCallback(() => {
    setAutoScanEnabled(prev => !prev)
  }, [])

  return {
    isSupported,
    isConnected,
    folderName,
    isScanning,
    autoScanEnabled,
    pickFolder,
    disconnect,
    scanFolder,
    toggleAutoScan
  }
}
