import axios from 'axios';

// ============== Types ==============

export interface SiteSummary {
    site: string;
    latest_total: number;
    delta_pct: number;
    issue_count: number;
    last_updated: string;
    // Health scoring fields
    health_score?: number;
    health_status?: 'critical' | 'warning' | 'healthy' | 'clean';
    room_flag_count?: number;
}

export interface InventorySummary {
    global_value: number;
    active_sites: number;
    total_issues: number;
    sites: SiteSummary[];
}

export type FileStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface FileRecord {
    id: string;
    filename: string;
    original_path: string;
    current_path: string;
    file_type: string;
    file_size: number;
    site_id: string | null;
    status: FileStatus;
    error_message: string | null;
    parsed_data: string | null;
    embedding_id: string | null;
    inventory_date: string | null;
    created_at: string;
    updated_at: string;
    processed_at: string | null;
}

export interface JobRecord {
    id: string;
    job_type: string;
    file_id: string | null;
    status: JobStatus;
    priority: number;
    attempts: number;
    max_attempts: number;
    error_message: string | null;
    result: string | null;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
}

export interface SearchResult {
    id: string;
    text: string;
    metadata: Record<string, unknown>;
    distance: number;
    score: number;
}

export interface SystemStats {
    files: Record<FileStatus, number>;
    jobs: Record<JobStatus, number>;
    embeddings: number;
}

export interface WorkerStatus {
    running: boolean;
    jobs: Array<{
        id: string;
        name: string;
        next_run: string | null;
    }>;
}

export interface EmbeddingStats {
    available: boolean;
    collection?: string;
    total_chunks?: number;
    model?: string;
    error?: string;
}

// ============== API Client ==============

export const api = axios.create({
    baseURL: '/api',
    timeout: 30000,  // 30 second timeout
});

// ============== Inventory API ==============

export const fetchSummary = async (): Promise<InventorySummary> => {
    const { data } = await api.get<InventorySummary>('/inventory/summary');
    return data;
};

export const fetchSiteDetail = async (siteId: string) => {
    const { data } = await api.get(`/inventory/sites/${encodeURIComponent(siteId)}`);
    return data;
};

// ============== File API ==============

export const uploadFile = async (file: File, siteId?: string): Promise<FileRecord> => {
    const formData = new FormData();
    formData.append('file', file);
    if (siteId) {
        formData.append('site_id', siteId);
    }
    const { data } = await api.post<{ success: boolean; file: FileRecord }>('/files/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data.file;
};

export const fetchFiles = async (params?: {
    status?: FileStatus;
    site_id?: string;
    limit?: number;
}): Promise<{ files: FileRecord[]; count: number }> => {
    const { data } = await api.get('/files', { params });
    return data;
};

export const fetchFile = async (fileId: string): Promise<FileRecord> => {
    const { data } = await api.get(`/files/${fileId}`);
    return data;
};

export const retryFile = async (fileId: string): Promise<FileRecord> => {
    const { data } = await api.post<{ success: boolean; file: FileRecord }>(`/files/${fileId}/retry`);
    return data.file;
};

export const deleteFile = async (fileId: string): Promise<{ success: boolean; embeddings_deleted: number }> => {
    const { data } = await api.delete(`/files/${fileId}`);
    return data;
};

export const reembedFile = async (fileId: string): Promise<{ success: boolean; job_id: string }> => {
    const { data } = await api.post(`/files/${fileId}/reembed`);
    return data;
};

export const downloadFile = async (fileId: string): Promise<Blob> => {
    const { data } = await api.get(`/files/${fileId}/download`, {
        responseType: 'blob'
    });
    return data;
};

export interface FileUpdateRequest {
    inventory_date?: string | null;
    site_id?: string | null;
    filename?: string;
}

export const updateFile = async (fileId: string, updates: FileUpdateRequest): Promise<FileRecord> => {
    const { data } = await api.patch<FileRecord>(`/files/${fileId}`, updates);
    return data;
};

// ============== Job API ==============

export const fetchJobs = async (params?: {
    status?: JobStatus;
    job_type?: string;
    limit?: number;
}): Promise<{ jobs: JobRecord[]; count: number }> => {
    const { data } = await api.get('/jobs', { params });
    return data;
};

export const fetchJob = async (jobId: string): Promise<JobRecord> => {
    const { data } = await api.get(`/jobs/${jobId}`);
    return data;
};

export const retryFailedJobs = async (): Promise<{ success: boolean; requeued_count: number }> => {
    const { data } = await api.post('/jobs/retry-failed');
    return data;
};

export const cancelJob = async (jobId: string): Promise<{ success: boolean; job: JobRecord }> => {
    const { data } = await api.post(`/jobs/${jobId}/cancel`);
    return data;
};

export const cancelAllJobs = async (): Promise<{ success: boolean; cancelled_count: number }> => {
    const { data } = await api.post('/jobs/cancel-all');
    return data;
};

// ============== Search API ==============

export interface SearchParams {
    query: string;
    limit?: number;
    fileId?: string;
    siteId?: string;
    dateFrom?: string;  // ISO date YYYY-MM-DD
    dateTo?: string;    // ISO date YYYY-MM-DD
    sortBy?: 'relevance' | 'date_desc' | 'date_asc' | 'site';
}

export const searchDocuments = async (
    query: string,
    limit: number = 10,
    fileId?: string,
    dateFrom?: string,
    dateTo?: string,
    sortBy: 'relevance' | 'date_desc' | 'date_asc' | 'site' = 'relevance',
    siteId?: string
): Promise<{ results: SearchResult[]; count: number; query: string }> => {
    const formData = new FormData();
    formData.append('query', query);
    formData.append('limit', limit.toString());
    formData.append('sort_by', sortBy);
    if (fileId) {
        formData.append('file_id', fileId);
    }
    if (siteId) {
        formData.append('site_id', siteId);
    }
    if (dateFrom) {
        formData.append('date_from', dateFrom);
    }
    if (dateTo) {
        formData.append('date_to', dateTo);
    }
    const { data } = await api.post('/search', formData);
    return data;
};

export const resetEmbeddings = async (): Promise<{ success: boolean; message: string }> => {
    const { data } = await api.post('/embeddings/reset');
    return data;
};

export const reindexEmbeddings = async (): Promise<{ success: boolean; message: string; queued_count: number }> => {
    const { data } = await api.post('/embeddings/reindex');
    return data;
};

export const findSimilar = async (
    fileId: string,
    chunk: number = 0,
    limit: number = 5
): Promise<{ results: SearchResult[]; count: number }> => {
    const { data } = await api.get(`/search/similar/${fileId}`, {
        params: { chunk, limit }
    });
    return data;
};

// ============== Stats API ==============

export const fetchStats = async (): Promise<SystemStats> => {
    const { data } = await api.get('/stats');
    return data;
};

export const fetchWorkerStatus = async (): Promise<WorkerStatus> => {
    const { data } = await api.get('/worker/status');
    return data;
};

export const fetchEmbeddingStats = async (): Promise<EmbeddingStats> => {
    const { data } = await api.get('/embeddings/stats');
    return data;
};

// ============== Analysis API ==============

export interface AnalysisResult {
    id: string;
    file_id: string;
    analysis_type: string;
    result: {
        summary?: string;
        anomalies?: string[];
        insights?: string[];
        risk_score?: number;
        risk_factors?: string[];
        value_change_pct?: number;
        alerts?: string[];
    };
    created_at: string;
}

export interface Anomaly {
    file_id: string;
    anomalies: string[];
    risk_score: number;
    summary: string;
    detected_at: string;
}

export interface SiteAnalysisSummary {
    site_id: string;
    file_count: number;
    latest_file: {
        filename: string;
        date: string;
        row_count: number;
        total_value: number;
    } | null;
    total_value: number;
    ai_summary: string | null;
    generated_at: string;
}

export const fetchAnalysisResults = async (params?: {
    file_id?: string;
    analysis_type?: string;
    limit?: number;
}): Promise<{ results: AnalysisResult[]; count: number }> => {
    const { data } = await api.get('/analysis/results', { params });
    return data;
};

export const fetchAnomalies = async (limit: number = 10): Promise<{ anomalies: Anomaly[]; count: number }> => {
    const { data } = await api.get('/analysis/anomalies', { params: { limit } });
    return data;
};

export const fetchFileAnalysis = async (fileId: string): Promise<{ file_id: string; analyses: AnalysisResult[] }> => {
    const { data } = await api.get(`/analysis/file/${fileId}`);
    return data;
};

export const triggerFileAnalysis = async (fileId: string): Promise<{ success: boolean; result_id: string; analysis: AnalysisResult['result'] }> => {
    const { data } = await api.post(`/analysis/file/${fileId}`);
    return data;
};

export const fetchSiteAnalysisSummary = async (siteId: string): Promise<SiteAnalysisSummary> => {
    const { data } = await api.get(`/analysis/site/${encodeURIComponent(siteId)}/summary`);
    return data;
};

// ============== Maintenance API ==============

export const runCleanup = async (days: number = 30): Promise<{ success: boolean; deleted_count: number }> => {
    const { data } = await api.post('/maintenance/cleanup', null, { params: { days } });
    return data;
};

// ============== Scores API ==============

export type ScoreStatus = 'critical' | 'warning' | 'healthy' | 'clean';
export type TrendType = 'up' | 'down' | 'stable' | null;
export type FlagType = 'uom_error' | 'big_dollar' | 'flagged_distributor';

export interface SourceFile {
    id: string;
    filename: string;
    processed_at: string | null;
}

export interface UnitScore {
    site_id: string;
    status: ScoreStatus;
    item_flags: number;
    total_value: number;
    last_scored: string;
    trend: TrendType;
    source_file: SourceFile | null;
}

export interface FlaggedItem {
    item: string;
    qty: number;
    uom: string;
    total: number;
    flags: FlagType[];
    points: number;
    location: string;
}

export interface UnitScoreDetail extends UnitScore {
    item_count: number;
    flagged_items: FlaggedItem[];
}

export interface ScoreHistoryEntry {
    id: string;
    site_id: string;
    score: number;
    status: ScoreStatus;
    item_flag_count: number;
    total_value: number;
    snapshot_date: string;
    created_at: string;
}

export const fetchScores = async (params?: {
    status?: ScoreStatus;
    limit?: number;
}): Promise<{ units: UnitScore[]; count: number }> => {
    const { data } = await api.get('/scores', { params });
    return data;
};

export const fetchSiteScore = async (siteId: string): Promise<UnitScoreDetail> => {
    const { data } = await api.get(`/scores/${encodeURIComponent(siteId)}`);
    return data;
};

export const fetchSiteFlaggedItems = async (siteId: string): Promise<{
    site_id: string;
    items: FlaggedItem[];
    count: number;
}> => {
    const { data } = await api.get(`/scores/${encodeURIComponent(siteId)}/items`);
    return data;
};

export const fetchScoreHistory = async (
    siteId: string,
    limit: number = 12
): Promise<{ site_id: string; history: ScoreHistoryEntry[]; count: number }> => {
    const { data } = await api.get(`/scores/${encodeURIComponent(siteId)}/history`, {
        params: { limit }
    });
    return data;
};

export const refreshScores = async (): Promise<{ success: boolean; message: string }> => {
    const { data } = await api.post('/scores/refresh');
    return data;
};

export const createScoreSnapshot = async (): Promise<{ success: boolean; message: string; snapshot_date: string; count: number }> => {
    const { data } = await api.post('/scores/snapshot');
    return data;
};

export const fetchSiteFiles = async (siteId: string): Promise<{ site_id: string; files: FileRecord[]; count: number }> => {
    const { data } = await api.get(`/scores/${encodeURIComponent(siteId)}/files`);
    return data;
};

// ============== Sites API ==============

export interface SiteInfo {
    site_id: string;
    display_name: string;
    is_custom: boolean;
    created_at?: string;
    updated_at?: string;
}

/**
 * Auto-format a site_id into a display name.
 * Converts underscores to spaces and applies smart capitalization.
 * Example: 'pseg_nhq' -> 'PSEG NHQ'
 */
export function formatSiteName(siteId: string): string {
    // Known abbreviations that should be uppercase
    const abbreviations = new Set([
        'pseg', 'nhq', 'hq', 'nyc', 'nj', 'usa', 'llc', 'inc', 'nw', 'ne', 'sw', 'se'
    ]);

    return siteId
        .split('_')
        .map(word => {
            if (abbreviations.has(word.toLowerCase())) {
                return word.toUpperCase();
            }
            // Title case for regular words
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        })
        .join(' ');
}

export const fetchSites = async (): Promise<{ sites: SiteInfo[]; count: number }> => {
    const { data } = await api.get('/sites');
    return data;
};

export const fetchSite = async (siteId: string): Promise<SiteInfo> => {
    const { data } = await api.get(`/sites/${encodeURIComponent(siteId)}`);
    return data;
};

export const updateSiteName = async (siteId: string, displayName: string | null): Promise<{ success: boolean; site: SiteInfo }> => {
    const formData = new FormData();
    if (displayName) {
        formData.append('display_name', displayName);
    }
    const { data } = await api.put(`/sites/${encodeURIComponent(siteId)}`, formData);
    return data;
};

// ============== Purchase Match API ==============

export type MatchFlagType = 'sku_mismatch' | 'orphan';

export interface PurchaseMatchStatus {
    initialized: boolean;
    canon_loaded: boolean;
    canon_record_count: number;
    inventory_loaded: boolean;
    available_units: string[];
}

export interface MatchSummary {
    total: number;
    clean: number;
    orderable: number;
    likely_typo: number;
    unknown: number;
    ignored: number;
    actionable: number;
    // Legacy
    sku_mismatch: number;
    orphan: number;
}

export interface ItemSuggestion {
    sku: string;
    description: string;
    vendor: string;
    price: number | null;
    similarity: number;  // 0-100 percentage
}

export interface CatalogInfo {
    vendor: string;
    description: string;
    price: number | null;
}

export interface MatchedItem {
    sku: string;
    description: string;
    quantity: number;
    price: number | null;
    vendor: string | null;
    reason: string;
    // For LIKELY_TYPO - full suggestion details
    suggestion?: ItemSuggestion;
    // For ORDERABLE - catalog info
    catalog?: CatalogInfo;
    // Legacy
    suggested_sku?: string;
    suggested_description?: string;
    suggested_price?: number;
}

export interface PurchaseMatchResult {
    unit: string;
    summary: MatchSummary;
    // New categories
    likely_typos: MatchedItem[];
    orderable: MatchedItem[];
    unknown: MatchedItem[];
    ignored: MatchedItem[];
    clean: MatchedItem[] | null;
    // Legacy
    mismatches: MatchedItem[];
    orphans: MatchedItem[];
}

export const fetchPurchaseMatchStatus = async (): Promise<PurchaseMatchStatus> => {
    const { data } = await api.get<PurchaseMatchStatus>('/purchase-match/status');
    return data;
};

export const fetchPurchaseMatchUnits = async (): Promise<{ units: string[] }> => {
    const { data } = await api.get<{ units: string[] }>('/purchase-match/units');
    return data;
};

export const runPurchaseMatch = async (unit: string, includeClean: boolean = false): Promise<PurchaseMatchResult> => {
    const { data } = await api.get<PurchaseMatchResult>(`/purchase-match/run/${encodeURIComponent(unit)}`, {
        params: { include_clean: includeClean }
    });
    return data;
};

export const reloadPurchaseMatch = async (): Promise<PurchaseMatchStatus> => {
    const { data } = await api.post<PurchaseMatchStatus>('/purchase-match/reload');
    return data;
};

export interface MOGSearchResult {
    sku: string;
    description: string;
    vendor: string;
    price: number | null;
    similarity: number;
}

export const searchMOGCatalog = async (query: string, limit: number = 10): Promise<{ query: string; results: MOGSearchResult[]; count: number }> => {
    const formData = new FormData();
    formData.append('query', query);
    formData.append('limit', limit.toString());
    const { data } = await api.post('/mog/search', formData);
    return data;
};

// ============== History API ==============

export interface HistoryTrend {
    change: number;
    percent?: number;
    direction: 'up' | 'down' | 'stable';
}

export interface SiteHistory {
    site_id: string;
    current: {
        total_value: number;
        item_count: number;
        item_flag_count: number;
        status: string;
    } | null;
    history: Array<{
        snapshot_date: string;
        total_value: number;
        item_flag_count: number;
        score: number;
        status: string;
    }>;
    trends: {
        value: HistoryTrend | null;
        flags: HistoryTrend | null;
    };
}

export interface Mover {
    sku: string;
    description: string;
    previous_qty: number;
    current_qty: number;
    change: number;
    direction: 'up' | 'down';
}

export interface MoversResponse {
    site_id: string;
    movers: Mover[];
    latest_file?: string;
    previous_file?: string;
    message?: string;
}

export interface AnomalyItem {
    sku: string;
    description: string;
    quantity: number;
    price: number;
}

export interface AnomaliesResponse {
    site_id: string;
    appeared: AnomalyItem[];
    vanished: AnomalyItem[];
    appeared_count: number;
    vanished_count: number;
    latest_file?: string;
    previous_file?: string;
    message?: string;
}

export const fetchSiteHistory = async (siteId: string, days: number = 30): Promise<SiteHistory> => {
    const { data } = await api.get<SiteHistory>(`/history/${encodeURIComponent(siteId)}`, {
        params: { days }
    });
    return data;
};

export const fetchSiteMovers = async (siteId: string, limit: number = 10): Promise<MoversResponse> => {
    const { data } = await api.get<MoversResponse>(`/history/${encodeURIComponent(siteId)}/movers`, {
        params: { limit }
    });
    return data;
};

export const fetchSiteAnomalies = async (siteId: string, limit: number = 20): Promise<AnomaliesResponse> => {
    const { data } = await api.get<AnomaliesResponse>(`/history/${encodeURIComponent(siteId)}/anomalies`, {
        params: { limit }
    });
    return data;
};

// ============== Ignore List API ==============

export interface IgnoredItem {
    id: string;
    site_id: string;
    sku: string;
    reason: string | null;
    notes: string | null;
    created_by: string | null;
    created_at: string;
}

export interface IgnoredItemsResponse {
    site_id: string;
    items: IgnoredItem[];
    count: number;
}

export const fetchIgnoredItems = async (siteId: string): Promise<IgnoredItemsResponse> => {
    const { data } = await api.get<IgnoredItemsResponse>(`/purchase-match/${encodeURIComponent(siteId)}/ignored`);
    return data;
};

export const addIgnoredItem = async (
    siteId: string,
    sku: string,
    reason?: string,
    notes?: string
): Promise<{ success: boolean; item: IgnoredItem }> => {
    const { data } = await api.post(`/purchase-match/${encodeURIComponent(siteId)}/ignore`, {
        sku,
        reason,
        notes
    });
    return data;
};

export const removeIgnoredItem = async (
    siteId: string,
    sku: string
): Promise<{ success: boolean; message: string }> => {
    const { data } = await api.delete(`/purchase-match/${encodeURIComponent(siteId)}/ignore/${encodeURIComponent(sku)}`);
    return data;
};

// ============== Collections API ==============

export interface CollectionInfo {
    name: string;
    description: string;
    icon: string;
    color: string;
    type: 'static' | 'expandable' | 'dynamic';
    chunk_count: number;
    exists: boolean;
}

export interface CollectionStats extends CollectionInfo {
    file_count: number;
    sites: string[];
    date_range: {
        earliest: string | null;
        latest: string | null;
    };
}

export const fetchCollections = async (): Promise<{ collections: CollectionInfo[]; count: number }> => {
    const { data } = await api.get('/collections');
    return data;
};

export const fetchCollectionStats = async (name: string): Promise<CollectionStats> => {
    const { data } = await api.get(`/collections/${name}`);
    return data;
};

export const migrateCollections = async (): Promise<{ success: boolean; message: string; migrated: number }> => {
    const { data } = await api.post('/collections/migrate');
    return data;
};

export const initCollections = async (): Promise<{ success: boolean; message: string; collections: CollectionInfo[] }> => {
    const { data } = await api.post('/collections/init');
    return data;
};

export const searchUnified = async (
    query: string,
    params?: {
        limit?: number;
        collections?: string[];
        dateFrom?: string;
        dateTo?: string;
        siteId?: string;
    }
): Promise<{ results: SearchResult[]; count: number; query: string }> => {
    const formData = new FormData();
    formData.append('query', query);
    if (params?.limit) formData.append('limit', params.limit.toString());
    if (params?.collections?.length) formData.append('collections', params.collections.join(','));
    if (params?.dateFrom) formData.append('date_from', params.dateFrom);
    if (params?.dateTo) formData.append('date_to', params.dateTo);
    if (params?.siteId) formData.append('site_id', params.siteId);

    const { data } = await api.post('/search/unified', formData);
    return data;
};

export const searchCollection = async (
    collectionName: string,
    query: string,
    params?: {
        limit?: number;
        fileId?: string;
        siteId?: string;
        dateFrom?: string;
        dateTo?: string;
        sortBy?: 'relevance' | 'date_desc' | 'date_asc' | 'site';
    }
): Promise<{ results: SearchResult[]; count: number; collection: string }> => {
    const formData = new FormData();
    formData.append('query', query);
    if (params?.limit) formData.append('limit', params.limit.toString());
    if (params?.fileId) formData.append('file_id', params.fileId);
    if (params?.siteId) formData.append('site_id', params.siteId);
    if (params?.dateFrom) formData.append('date_from', params.dateFrom);
    if (params?.dateTo) formData.append('date_to', params.dateTo);
    if (params?.sortBy) formData.append('sort_by', params.sortBy);

    const { data } = await api.post(`/search/${collectionName}`, formData);
    return data;
};

// ============== Day At A Glance API ==============

export interface GlanceItem {
    id: string;
    content: string;
    metadata: Record<string, unknown>;
}

export interface DayGlance {
    date: string;
    schedules: GlanceItem[];
    notes: GlanceItem[];
    files: GlanceItem[];
    people_working: string[];
    tags: string[];
}

export interface Briefing {
    date: string;
    schedule_count: number;
    note_count: number;
    people_working: string[];
    tags: string[];
    recent_anomalies: Anomaly[];
    summary: string | null;
}

export const fetchGlance = async (date?: string): Promise<DayGlance> => {
    const params = date ? { date } : {};
    const { data } = await api.get('/glance', { params });
    return data;
};

export const fetchUpcomingGlance = async (days: number = 7): Promise<{ days: DayGlance[]; count: number }> => {
    const { data } = await api.get('/glance/upcoming', { params: { days } });
    return data;
};

export const fetchBriefing = async (date?: string): Promise<Briefing> => {
    const params = date ? { date } : {};
    const { data } = await api.get('/glance/briefing', { params });
    return data;
};

export const createMemoryNote = async (
    content: string,
    title?: string,
    tags?: string[]
): Promise<{ success: boolean; note_id: string; title: string; metadata: Record<string, unknown> }> => {
    const formData = new FormData();
    formData.append('content', content);
    if (title) formData.append('title', title);
    if (tags?.length) formData.append('tags', tags.join(','));

    const { data } = await api.post('/memory/note', formData);
    return data;
};

// ============== Shopping Cart API ==============

export interface CartItem {
    id: string;
    site_id: string;
    sku: string;
    description: string;
    quantity: number;
    unit_price: number | null;
    uom: string | null;
    vendor: string | null;
    notes: string | null;
    source: string;
    created_at: string;
    updated_at: string;
}

export interface CartSummary {
    site_id: string;
    item_count: number;
    total_quantity: number;
    total_value: number;
}

export interface CartResponse {
    site_id: string;
    items: CartItem[];
    summary: CartSummary;
}

export const fetchCart = async (siteId: string): Promise<CartResponse> => {
    const { data } = await api.get(`/cart/${siteId}`);
    return data;
};

export const addToCart = async (
    siteId: string,
    item: {
        sku: string;
        description: string;
        quantity?: number;
        unit_price?: number;
        uom?: string;
        vendor?: string;
        notes?: string;
        source?: string;
    }
): Promise<{ success: boolean; item: CartItem }> => {
    const { data } = await api.post(`/cart/${siteId}/add`, item);
    return data;
};

export const bulkAddToCart = async (
    siteId: string,
    items: Array<{
        sku: string;
        description: string;
        quantity?: number;
        unit_price?: number;
        uom?: string;
        vendor?: string;
        notes?: string;
    }>,
    source: string = 'bulk'
): Promise<{ success: boolean; added_count: number; summary: CartSummary }> => {
    const { data } = await api.post(`/cart/${siteId}/bulk`, { items, source });
    return data;
};

export const updateCartItemQuantity = async (
    siteId: string,
    sku: string,
    quantity: number
): Promise<{ success: boolean; item: CartItem }> => {
    const formData = new FormData();
    formData.append('quantity', quantity.toString());
    const { data } = await api.put(`/cart/${siteId}/${encodeURIComponent(sku)}`, formData);
    return data;
};

export const removeFromCart = async (
    siteId: string,
    sku: string
): Promise<{ success: boolean; message: string }> => {
    const { data } = await api.delete(`/cart/${siteId}/${encodeURIComponent(sku)}`);
    return data;
};

export const clearCart = async (
    siteId: string
): Promise<{ success: boolean; cleared_count: number }> => {
    const { data } = await api.delete(`/cart/${siteId}`);
    return data;
};

// ============== Count Session API ==============

export interface CountSession {
    id: string;
    site_id: string;
    name: string;
    status: 'active' | 'completed' | 'exported';
    item_count: number;
    total_value: number;
    created_at: string;
    updated_at: string;
    completed_at: string | null;
}

export interface CountItem {
    id: string;
    session_id: string;
    sku: string;
    description: string;
    counted_qty: number;
    expected_qty: number | null;
    unit_price: number | null;
    uom: string | null;
    location: string | null;
    variance: number | null;
    notes: string | null;
    counted_at: string;
}

export const fetchCountSessions = async (params?: {
    siteId?: string;
    status?: string;
    limit?: number;
}): Promise<{ sessions: CountSession[]; count: number }> => {
    const { data } = await api.get('/count-sessions', {
        params: {
            site_id: params?.siteId,
            status: params?.status,
            limit: params?.limit
        }
    });
    return data;
};

export const createCountSession = async (
    siteId: string,
    name?: string
): Promise<{ success: boolean; session: CountSession }> => {
    const formData = new FormData();
    formData.append('site_id', siteId);
    if (name) formData.append('name', name);
    const { data } = await api.post('/count-sessions', formData);
    return data;
};

export const fetchCountSession = async (
    sessionId: string
): Promise<{ session: CountSession; items: CountItem[]; item_count: number }> => {
    const { data } = await api.get(`/count-sessions/${sessionId}`);
    return data;
};

export const updateCountSession = async (
    sessionId: string,
    updates: { status?: string; name?: string }
): Promise<{ success: boolean; session: CountSession }> => {
    const formData = new FormData();
    if (updates.status) formData.append('status', updates.status);
    if (updates.name) formData.append('name', updates.name);
    const { data } = await api.put(`/count-sessions/${sessionId}`, formData);
    return data;
};

export const addCountItem = async (
    sessionId: string,
    item: {
        sku: string;
        description: string;
        counted_qty: number;
        expected_qty?: number;
        unit_price?: number;
        uom?: string;
        location?: string;
        notes?: string;
    }
): Promise<{ success: boolean; item: CountItem }> => {
    const { data } = await api.post(`/count-sessions/${sessionId}/items`, item);
    return data;
};

export const deleteCountSession = async (
    sessionId: string
): Promise<{ success: boolean; message: string }> => {
    const { data } = await api.delete(`/count-sessions/${sessionId}`);
    return data;
};

export const populateCountFromInventory = async (
    sessionId: string
): Promise<{ success: boolean; added_count: number; session: CountSession; items: CountItem[] }> => {
    const { data } = await api.post(`/count-sessions/${sessionId}/populate-from-inventory`);
    return data;
};

// ============== Inventory Items API (from valuation files) ==============

export interface InventoryItemsResponse {
    items: InventoryItem[];
    count: number;
    total_in_file: number;
    source_file: string;
    file_date: string;
}

export const fetchInventoryItems = async (
    siteId: string,
    limit?: number
): Promise<InventoryItemsResponse> => {
    const { data } = await api.get(`/inventory/sites/${siteId}/items`, {
        params: { limit }
    });
    return data;
};

// ============== Inventory Snapshot API (Safe State Return) ==============

export interface InventorySnapshot {
    id: string;
    site_id: string;
    name: string;
    source_file_id: string | null;
    snapshot_data: InventoryItem[];
    item_count: number;
    total_value: number;
    status: 'active' | 'restored' | 'archived';
    created_at: string;
}

export interface InventoryItem {
    sku: string;
    description: string;
    quantity: number;
    uom: string | null;
    unit_price: number | null;
    vendor: string | null;
    location: string | null;
}

export const fetchInventorySnapshots = async (
    siteId: string,
    status?: string,
    limit?: number
): Promise<{ snapshots: Omit<InventorySnapshot, 'snapshot_data'>[]; count: number }> => {
    const { data } = await api.get(`/inventory/snapshots/${siteId}`, {
        params: { status, limit }
    });
    return data;
};

export const fetchLatestSnapshot = async (
    siteId: string
): Promise<InventorySnapshot> => {
    const { data } = await api.get(`/inventory/snapshots/${siteId}/latest`);
    return data;
};

export const fetchSnapshot = async (
    snapshotId: string
): Promise<InventorySnapshot> => {
    const { data } = await api.get(`/inventory/snapshot/${snapshotId}`);
    return data;
};

export const restoreSnapshot = async (
    snapshotId: string
): Promise<{ success: boolean; message: string; snapshot: InventorySnapshot }> => {
    const { data } = await api.post(`/inventory/snapshot/${snapshotId}/restore`);
    return data;
};

export const deleteSnapshot = async (
    snapshotId: string
): Promise<{ success: boolean; message: string }> => {
    const { data } = await api.delete(`/inventory/snapshot/${snapshotId}`);
    return data;
};

// ============== Auto-Clean & Purchase Match Integration ==============

export interface CleanedInventoryResult {
    site_id: string;
    snapshot_id: string | null;
    original_count: number;
    cleaned_count: number;
    fixes_applied: Array<{
        original_sku: string;
        corrected_sku: string;
        description: string;
        similarity: number;
    }>;
    cleaned_items: InventoryItem[];
}

export const autoCleanInventory = async (
    siteId: string,
    options?: {
        createSnapshot?: boolean;
        applyTypoFixes?: boolean;
    }
): Promise<CleanedInventoryResult> => {
    const formData = new FormData();
    formData.append('create_snapshot', (options?.createSnapshot ?? true).toString());
    formData.append('apply_typo_fixes', (options?.applyTypoFixes ?? true).toString());
    const { data } = await api.post(`/inventory/auto-clean/${siteId}`, formData);
    return data;
};

export const addPurchaseMatchToCart = async (
    siteId: string,
    category: 'orderable' | 'likely_typos' | 'unknown',
    applyCorrections: boolean = true
): Promise<{ success: boolean; added_count: number; category: string; summary: CartSummary }> => {
    const formData = new FormData();
    formData.append('category', category);
    formData.append('apply_corrections', applyCorrections.toString());
    const { data } = await api.post(`/purchase-match/${siteId}/add-to-cart`, formData);
    return data;
};

// ============== Export API ==============

export const exportCart = (siteId: string): string => {
    return `${api.defaults.baseURL}/export/cart/${siteId}`;
};

export const exportCountSession = (sessionId: string): string => {
    return `${api.defaults.baseURL}/export/count-session/${sessionId}`;
};

export const exportInventory = async (
    siteId: string,
    options?: {
        includeModifications?: boolean;
        items?: Array<{
            sku: string;
            description: string;
            quantity: number;
            uom?: string;
            unit_price?: number;
            location?: string;
        }>;
    }
): Promise<Blob> => {
    const formData = new FormData();
    if (options?.includeModifications) {
        formData.append('include_modifications', 'true');
    }
    if (options?.items) {
        formData.append('items', JSON.stringify(options.items));
    }

    const response = await api.post(`/export/inventory/${siteId}`, formData, {
        responseType: 'blob'
    });
    return response.data;
};

// Helper function to trigger download of a blob
export const saveBlobAsFile = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
};

// ============== Off-Catalog API ==============

export interface OffCatalogItem {
    id: string;
    site_id: string;
    dist_num: string;
    cust_num: string;
    description: string;
    pack: string;
    uom: string;
    break_uom?: string;
    unit_price?: number;
    break_price?: number;
    distributor: string;
    distribution_center?: string;
    brand?: string;
    manufacturer?: string;
    manufacturer_num?: string;
    gtin?: string;
    upc?: string;
    catch_weight?: number;
    average_weight?: number;
    units_per_case?: number;
    location?: string;
    area?: string;
    place?: string;
    notes?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface OffCatalogItemRequest {
    dist_num: string;
    cust_num?: string;
    description?: string;
    pack?: string;
    uom?: string;
    break_uom?: string;
    unit_price?: number;
    break_price?: number;
    distributor?: string;
    distribution_center?: string;
    brand?: string;
    manufacturer?: string;
    manufacturer_num?: string;
    gtin?: string;
    upc?: string;
    catch_weight?: number;
    average_weight?: number;
    units_per_case?: number;
    location?: string;
    area?: string;
    place?: string;
    notes?: string;
}

export const fetchOffCatalogItems = async (
    siteId: string,
    includeInactive: boolean = false
): Promise<{ items: OffCatalogItem[]; count: number }> => {
    const { data } = await api.get(`/off-catalog/${siteId}`, {
        params: { include_inactive: includeInactive }
    });
    return data;
};

export const createOffCatalogItem = async (
    siteId: string,
    item: OffCatalogItemRequest
): Promise<{ success: boolean; item: OffCatalogItem }> => {
    const { data } = await api.post(`/off-catalog/${siteId}`, item);
    return data;
};

export const updateOffCatalogItem = async (
    siteId: string,
    custNum: string,
    item: OffCatalogItemRequest
): Promise<{ success: boolean; item: OffCatalogItem }> => {
    const { data } = await api.put(`/off-catalog/${siteId}/${custNum}`, item);
    return data;
};

export const deleteOffCatalogItem = async (
    siteId: string,
    custNum: string,
    hardDelete: boolean = false
): Promise<{ success: boolean; message: string }> => {
    const { data } = await api.delete(`/off-catalog/${siteId}/${custNum}`, {
        params: { hard_delete: hardDelete }
    });
    return data;
};

export const generateCustNum = async (
    siteId: string,
    prefix: string = 'SPEC'
): Promise<{ cust_num: string }> => {
    const { data } = await api.post(`/off-catalog/${siteId}/generate-cust-num`, null, {
        params: { prefix }
    });
    return data;
};

// ============== Rooms API ==============

export interface RoomInfo {
    id?: string;
    name: string;
    display_name: string;
    sort_order: number;
    item_count: number;
    is_predefined: boolean;
    color?: string;
    is_active: boolean;
}

export interface RoomInventoryItem {
    sku: string;
    description: string;
    quantity: number;
    unit_price?: number;
    uom?: string;
    vendor?: string;
    location: string;
    auto_assigned: boolean;
    sort_order: number;
}

export interface RoomWithItems extends RoomInfo {
    items: RoomInventoryItem[];
}

export interface ItemLocation {
    id: string;
    site_id: string;
    sku: string;
    location: string;
    zone?: string;
    sort_order: number;
    never_count: boolean;
    auto_assigned: boolean;
    created_at: string;
    updated_at: string;
}

export interface CreateRoomRequest {
    name: string;
    display_name?: string;
    sort_order?: number;
    color?: string;
}

export interface MoveItemRequest {
    room: string;
    sort_order?: number;
}

export const fetchRooms = async (
    siteId: string,
    includeEmpty: boolean = true
): Promise<{ rooms: RoomInfo[]; count: number }> => {
    const { data } = await api.get(`/rooms/${siteId}`, {
        params: { include_empty: includeEmpty }
    });
    return data;
};

export const fetchRoom = async (
    siteId: string,
    roomName: string
): Promise<{ room: RoomInfo }> => {
    const { data } = await api.get(`/rooms/${siteId}/${encodeURIComponent(roomName)}`);
    return data;
};

export const createRoom = async (
    siteId: string,
    room: CreateRoomRequest
): Promise<{ success: boolean; room: RoomInfo }> => {
    const { data } = await api.post(`/rooms/${siteId}`, room);
    return data;
};

export const updateRoom = async (
    siteId: string,
    roomName: string,
    updates: Partial<CreateRoomRequest>
): Promise<{ success: boolean; room: RoomInfo }> => {
    const { data } = await api.put(`/rooms/${siteId}/${encodeURIComponent(roomName)}`, updates);
    return data;
};

export const deleteRoom = async (
    siteId: string,
    roomName: string,
    moveItemsTo: string = 'UNASSIGNED'
): Promise<{ success: boolean; message: string }> => {
    const { data } = await api.delete(`/rooms/${siteId}/${encodeURIComponent(roomName)}`, {
        params: { move_items_to: moveItemsTo }
    });
    return data;
};

export const fetchItemsByRoom = async (
    siteId: string,
    includeEmptyRooms: boolean = true
): Promise<{ rooms: RoomWithItems[]; count: number }> => {
    const { data } = await api.get(`/rooms/${siteId}/items/all`, {
        params: { include_empty_rooms: includeEmptyRooms }
    });
    return data;
};

export const moveItemToRoom = async (
    siteId: string,
    sku: string,
    room: string,
    sortOrder: number = 0
): Promise<{ success: boolean; item_location: ItemLocation }> => {
    const { data } = await api.put(`/rooms/${siteId}/items/${encodeURIComponent(sku)}`, {
        room,
        sort_order: sortOrder
    });
    return data;
};

export const bulkMoveItems = async (
    siteId: string,
    moves: Array<{ sku: string; room: string; sort_order?: number }>
): Promise<{ success: boolean; moved: number; errors: number }> => {
    const { data } = await api.put(`/rooms/${siteId}/items/bulk/move`, { moves });
    return data;
};

// ============== GL Codes API ==============

export const fetchGLCodes = async (
    siteId: string
): Promise<{ gl_codes: string[]; count: number; source_file?: string }> => {
    const { data } = await api.get(`/inventory/sites/${siteId}/gl-codes`);
    return data;
};
