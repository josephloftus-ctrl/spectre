// Core types for the unified Spectre database

export type TagType = 'system' | 'user'
export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'error'
export type NoteCategory = 'inventory' | 'temps' | 'todo' | 'order' | 'general'

// Tags - shared across documents and notes
export interface Tag {
  id: string
  name: string
  color: string
  type: TagType
  staleDays?: number // After this many days, items with this tag are "stale"
}

// Documents - parsed Excel/PDF files
export interface Document {
  id: string
  filename: string
  fileType: 'xlsx' | 'pdf' | 'csv'
  fileSize: number
  siteId?: string
  siteName?: string

  // Parsing status
  status: DocumentStatus
  errorMessage?: string

  // Parsed data
  totalValue?: number
  itemCount?: number
  parsedData?: Record<string, unknown>

  // Timestamps
  receivedAt: string
  processedAt?: string

  // Organization
  tags: string[] // Tag IDs

  // Source
  emailId?: string // If from Outlook
  emailSubject?: string
  emailFrom?: string

  // Raw file (stored as blob)
  fileBlob?: Blob
}

// Notes - quick capture text/voice
export interface Note {
  id: string
  content: string
  title: string
  category?: NoteCategory

  // Linked to a document?
  documentId?: string

  // Organization
  tags: string[]

  // Timestamps
  createdAt: string
  updatedAt: string

  // Sync state
  deleted: boolean
  pendingSync: boolean
  syncedAt?: string

  // Voice input
  isVoiceNote?: boolean
}

// Sites - inventory locations
export interface Site {
  id: string
  name: string
  aliases: string[] // Alternative names for matching
  latestTotal?: number
  lastUpdated?: string
}

// Emails - cached from Microsoft Graph
export interface Email {
  id: string
  graphId: string // Microsoft Graph message ID
  subject: string
  from: string
  receivedAt: string
  hasAttachments: boolean
  attachmentNames: string[]
  processed: boolean // Have we downloaded/processed this?
}

// Sync queue for offline actions
export type SyncAction = 'CREATE_NOTE' | 'UPDATE_NOTE' | 'DELETE_NOTE' | 'PROCESS_DOCUMENT'

export interface SyncQueueItem {
  id: string
  action: SyncAction
  targetId: string
  payload: Record<string, unknown>
  createdAt: string
  retryCount: number
}

// Chat sessions - persistent AI conversations
export interface ChatSession {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messageCount: number
  // Summary for memory context
  summary?: string
  // Archived sessions don't appear in main list
  archived: boolean
}

// Chat messages - individual messages in a session
export interface ChatMessage {
  id: string
  sessionId: string
  role: 'user' | 'assistant' | 'system'
  content: string
  createdAt: string
  // For tracking which model responded
  model?: string
}

// Memory context - extracted insights from past conversations
export interface MemoryItem {
  id: string
  content: string
  category: 'fact' | 'preference' | 'procedure' | 'issue'
  source: 'chat' | 'note' | 'manual'
  sourceId?: string
  createdAt: string
  importance: number // 1-5, higher = more important
}

// Default system tags
export const DEFAULT_TAGS: Omit<Tag, 'id'>[] = [
  { name: 'orders', color: '#3b82f6', type: 'system', staleDays: 3 },
  { name: 'inventory', color: '#22c55e', type: 'system', staleDays: 14 },
  { name: 'tasks', color: '#f59e0b', type: 'system' },
  { name: 'notes', color: '#8b5cf6', type: 'system' },
  { name: 'money', color: '#10b981', type: 'system' },
  { name: 'urgent', color: '#ef4444', type: 'system', staleDays: 1 },
]
