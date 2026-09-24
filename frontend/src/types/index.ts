// ============================================================
// 请求类型
// ============================================================

export interface AnalysisRequest {
  competitor?: string          // 单竞品（兼容）
  competitors?: string[]       // 多竞品
  industry?: string
  domain: string
  focus_areas?: string[]
}


// ============================================================
// 响应类型
// ============================================================

export interface AnalysisResponse {
  report_id: string
  competitor: string
  status: string
  message: string
}

export interface TodoItem {
  id: number
  title: string
  intent: string
  query: string
  status: 'pending' | 'running' | 'completed' | 'failed'
}

export interface SourceItem {
  title: string
  url: string
  snippet: string
}

export interface TaskSummary {
  competitor: string
  task_id: number
  title: string
  summary: string
  sources: SourceItem[]
}

export interface ReportDetail {
  report_id: string
  competitor: string
  industry?: string
  domain?: string
  created_at: string
  report: string
  report_type: 'single' | 'comparison'
  tasks: TodoItem[]
  summaries: TaskSummary[]
  all_sources: SourceItem[]
  competitors: string[]
  comparison_mode: boolean
  comparison_matrix?: Record<string, Record<string, string>>
  comparison_insights?: string
  duration_seconds: number
}

export interface HistoryItem {
  report_id: string
  competitor: string
  industry?: string
  created_at: string
  status: string
}

export interface HistoryResponse {
  items: HistoryItem[]
  total: number
}

// ============================================================
// SSE 事件类型
// ============================================================

export interface SSEEvent {
  type: 'start' | 'tasks' | 'status' | 'summary' | 'report' | 'error' | 'done'
  data?: any
  message?: string
}