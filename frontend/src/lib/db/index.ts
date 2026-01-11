import Dexie, { Table } from 'dexie'
import { Document, Note, Tag, Site, Email, SyncQueueItem, DEFAULT_TAGS, ChatSession, ChatMessage, MemoryItem } from './types'

export * from './types'

class SpectreDatabase extends Dexie {
  documents!: Table<Document>
  notes!: Table<Note>
  tags!: Table<Tag>
  sites!: Table<Site>
  emails!: Table<Email>
  syncQueue!: Table<SyncQueueItem>
  chatSessions!: Table<ChatSession>
  chatMessages!: Table<ChatMessage>
  memory!: Table<MemoryItem>

  constructor() {
    super('spectre')

    this.version(1).stores({
      documents: 'id, siteId, status, receivedAt, processedAt, *tags, emailId',
      notes: 'id, documentId, createdAt, updatedAt, deleted, pendingSync, *tags, category',
      tags: 'id, name, type',
      sites: 'id, name, *aliases',
      emails: 'id, graphId, receivedAt, processed',
      syncQueue: 'id, action, targetId, createdAt'
    })

    this.version(2).stores({
      chatSessions: 'id, createdAt, updatedAt, archived',
      chatMessages: 'id, sessionId, createdAt',
      memory: 'id, category, importance, createdAt'
    })

    // Seed default tags on first open
    this.on('ready', async () => {
      const tagCount = await this.tags.count()
      if (tagCount === 0) {
        await this.seedDefaultTags()
      }
    })
  }

  private async seedDefaultTags() {
    const tags: Tag[] = DEFAULT_TAGS.map((tag) => ({
      ...tag,
      id: `tag_${tag.name}`
    }))
    await this.tags.bulkAdd(tags)
  }
}

export const db = new SpectreDatabase()

// ============ NOTES CRUD ============

export async function createNote(content: string, options?: {
  documentId?: string
  tags?: string[]
  category?: Note['category']
  isVoiceNote?: boolean
}): Promise<Note> {
  const now = new Date().toISOString()
  const note: Note = {
    id: crypto.randomUUID(),
    content,
    title: content.split('\n')[0].slice(0, 50) || 'Untitled',
    documentId: options?.documentId,
    tags: options?.tags || [],
    category: options?.category,
    isVoiceNote: options?.isVoiceNote,
    createdAt: now,
    updatedAt: now,
    deleted: false,
    pendingSync: true
  }
  await db.notes.add(note)
  return note
}

export async function updateNote(id: string, updates: Partial<Pick<Note, 'content' | 'tags' | 'category'>>): Promise<void> {
  const updateData: Partial<Note> = {
    ...updates,
    updatedAt: new Date().toISOString(),
    pendingSync: true
  }
  if (updates.content) {
    updateData.title = updates.content.split('\n')[0].slice(0, 50) || 'Untitled'
  }
  await db.notes.update(id, updateData)
}

export async function deleteNote(id: string): Promise<void> {
  await db.notes.update(id, {
    deleted: true,
    updatedAt: new Date().toISOString(),
    pendingSync: true
  })
}

export async function getNotes(): Promise<Note[]> {
  return db.notes
    .filter(note => !note.deleted)
    .reverse()
    .sortBy('updatedAt')
}

export async function getNotesByDocument(documentId: string): Promise<Note[]> {
  return db.notes
    .where('documentId')
    .equals(documentId)
    .filter(note => !note.deleted)
    .toArray()
}

export async function searchNotes(query: string): Promise<Note[]> {
  const lower = query.toLowerCase()
  const notes = await getNotes()
  return notes.filter(note =>
    note.content.toLowerCase().includes(lower) ||
    note.title.toLowerCase().includes(lower)
  )
}

// ============ DOCUMENTS CRUD ============

export async function createDocument(data: Omit<Document, 'id'>): Promise<Document> {
  const doc: Document = {
    ...data,
    id: crypto.randomUUID()
  }
  await db.documents.add(doc)
  return doc
}

export async function updateDocument(id: string, updates: Partial<Document>): Promise<void> {
  await db.documents.update(id, updates)
}

export async function getDocuments(): Promise<Document[]> {
  return db.documents
    .orderBy('receivedAt')
    .reverse()
    .toArray()
}

export async function getDocumentsBySite(siteId: string): Promise<Document[]> {
  return db.documents
    .where('siteId')
    .equals(siteId)
    .reverse()
    .sortBy('receivedAt')
}

// ============ TAGS CRUD ============

export async function getTags(): Promise<Tag[]> {
  return db.tags.toArray()
}

export async function createTag(name: string, color: string): Promise<Tag> {
  const tag: Tag = {
    id: crypto.randomUUID(),
    name: name.toLowerCase().trim(),
    color,
    type: 'user'
  }
  await db.tags.add(tag)
  return tag
}

export async function deleteTag(id: string): Promise<void> {
  // Only delete user tags
  const tag = await db.tags.get(id)
  if (tag?.type === 'user') {
    await db.tags.delete(id)
  }
}

// ============ SITES CRUD ============

export async function getSites(): Promise<Site[]> {
  return db.sites.toArray()
}

export async function createOrUpdateSite(name: string, aliases?: string[]): Promise<Site> {
  const existing = await db.sites.where('name').equalsIgnoreCase(name).first()
  if (existing) {
    if (aliases) {
      const mergedAliases = [...new Set([...existing.aliases, ...aliases])]
      await db.sites.update(existing.id, { aliases: mergedAliases })
    }
    return existing
  }

  const site: Site = {
    id: crypto.randomUUID(),
    name,
    aliases: aliases || []
  }
  await db.sites.add(site)
  return site
}

// ============ EMAILS CRUD ============

export async function cacheEmails(emails: Omit<Email, 'id'>[]): Promise<void> {
  const existing = await db.emails.toArray()
  const existingGraphIds = new Set(existing.map(e => e.graphId))

  const newEmails: Email[] = emails
    .filter(e => !existingGraphIds.has(e.graphId))
    .map(e => ({
      ...e,
      id: crypto.randomUUID()
    }))

  if (newEmails.length > 0) {
    await db.emails.bulkAdd(newEmails)
  }
}

export async function getUnprocessedEmails(): Promise<Email[]> {
  return db.emails
    .where('processed')
    .equals(0) // false
    .toArray()
}

export async function markEmailProcessed(id: string): Promise<void> {
  await db.emails.update(id, { processed: true })
}

// ============ SYNC QUEUE ============

export async function enqueueSync(action: SyncQueueItem['action'], targetId: string, payload: Record<string, unknown> = {}): Promise<void> {
  const item: SyncQueueItem = {
    id: crypto.randomUUID(),
    action,
    targetId,
    payload,
    createdAt: new Date().toISOString(),
    retryCount: 0
  }
  await db.syncQueue.add(item)
}

export async function getSyncQueue(): Promise<SyncQueueItem[]> {
  return db.syncQueue.orderBy('createdAt').toArray()
}

export async function removeSyncItem(id: string): Promise<void> {
  await db.syncQueue.delete(id)
}

export async function incrementRetryCount(id: string): Promise<void> {
  const item = await db.syncQueue.get(id)
  if (item) {
    await db.syncQueue.update(id, { retryCount: item.retryCount + 1 })
  }
}

// ============ STATS ============

export async function getStats(): Promise<{
  documentCount: number
  noteCount: number
  pendingSyncCount: number
}> {
  const [documentCount, notes, syncQueue] = await Promise.all([
    db.documents.count(),
    db.notes.filter(n => !n.deleted).count(),
    db.syncQueue.count()
  ])

  const pendingNotes = await db.notes.where('pendingSync').equals(1).count()

  return {
    documentCount,
    noteCount: notes,
    pendingSyncCount: pendingNotes + syncQueue
  }
}

// ============ CHAT CRUD ============

export async function createChatSession(title?: string): Promise<ChatSession> {
  const now = new Date().toISOString()
  const session: ChatSession = {
    id: crypto.randomUUID(),
    title: title || 'New Chat',
    createdAt: now,
    updatedAt: now,
    messageCount: 0,
    archived: false
  }
  await db.chatSessions.add(session)
  return session
}

export async function getChatSessions(): Promise<ChatSession[]> {
  return db.chatSessions.where('archived').equals(0).reverse().sortBy('updatedAt')
}

export async function getChatMessages(sessionId: string): Promise<ChatMessage[]> {
  return db.chatMessages.where('sessionId').equals(sessionId).sortBy('createdAt')
}

export async function addChatMessage(sessionId: string, role: 'user' | 'assistant', content: string, model?: string, provider?: 'ollama' | 'claude'): Promise<ChatMessage> {
  const msg: ChatMessage = {
    id: crypto.randomUUID(),
    sessionId,
    role,
    content,
    createdAt: new Date().toISOString(),
    model,
    provider
  }
  await db.chatMessages.add(msg)
  await db.chatSessions.update(sessionId, {
    updatedAt: msg.createdAt,
    messageCount: await db.chatMessages.where('sessionId').equals(sessionId).count()
  })
  return msg
}

export async function updateSessionTitle(sessionId: string, title: string): Promise<void> {
  await db.chatSessions.update(sessionId, { title })
}

export async function archiveSession(sessionId: string): Promise<void> {
  await db.chatSessions.update(sessionId, { archived: true })
}

export async function deleteSession(sessionId: string): Promise<void> {
  await db.chatMessages.where('sessionId').equals(sessionId).delete()
  await db.chatSessions.delete(sessionId)
}

// ============ MEMORY CRUD ============

export async function addMemory(content: string, category: MemoryItem['category'], importance = 3): Promise<MemoryItem> {
  const item: MemoryItem = {
    id: crypto.randomUUID(),
    content,
    category,
    source: 'chat',
    createdAt: new Date().toISOString(),
    importance
  }
  await db.memory.add(item)
  return item
}

export async function getMemory(limit = 20): Promise<MemoryItem[]> {
  return db.memory.orderBy('importance').reverse().limit(limit).toArray()
}

export async function deleteMemory(id: string): Promise<void> {
  await db.memory.delete(id)
}
