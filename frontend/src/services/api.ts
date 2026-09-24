
import axios from 'axios'
import type {
  AnalysisRequest,
  AnalysisResponse,
  ReportDetail,
  HistoryResponse,
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,  // 5 分钟，因为分析可能耗时较长
})

// ============================================================
// 请求拦截器
// ============================================================
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => Promise.reject(error)
)

// ============================================================
// 响应拦截器
// ============================================================
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// ============================================================
// 同步分析
// ============================================================
export const startAnalysis = async (req: AnalysisRequest): Promise<AnalysisResponse> => {
  const response = await api.post<AnalysisResponse>('/analysis/start', req)
  return response.data
}

// ============================================================
// 获取报告
// ============================================================
export const getReport = async (reportId: string): Promise<ReportDetail> => {
  const response = await api.get<ReportDetail>(`/analysis/${reportId}`)
  return response.data
}

// ============================================================
// 获取历史
// ============================================================
export const getHistory = async (limit = 20): Promise<HistoryResponse> => {
  const response = await api.get<HistoryResponse>('/history', {
    params: { limit },
  })
  return response.data
}

// ============================================================
// 删除历史
// ============================================================
export const deleteHistory = async (reportId: string): Promise<void> => {
  await api.delete(`/history/${reportId}`)
}

// ============================================================
// SSE 流式分析
// ============================================================
export interface SSEHandlers {
  onStart?: (data: { report_id: string; competitor: string }) => void
  onTasks?: (tasks: any[]) => void
  onStatus?: (message: string) => void
  onSummary?: (data: any) => void
  onReport?: (report: string) => void
  onDone?: (data: { report_id: string; duration_seconds: number }) => void
  onError?: (message: string) => void
}

export const streamAnalysis = (
  req: AnalysisRequest,
  handlers: SSEHandlers
): (() => void) => {
  const controller = new AbortController()

  fetch('/api/analysis/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || '' // 保留最后一个不完整的

        for (const block of lines) {
          if (!block.startsWith('data: ')) continue
          try {
            const event = JSON.parse(block.slice(6))
            switch (event.type) {
              case 'start':
                handlers.onStart?.(event.data)
                break
              case 'tasks':
                handlers.onTasks?.(event.data.tasks)
                break
              case 'status':
                handlers.onStatus?.(event.message)
                break
              case 'summary':
                handlers.onSummary?.(event.data)
                break
              case 'report':
                handlers.onReport?.(event.data.report)
                break
              case 'done':
                handlers.onDone?.(event.data)
                break
              case 'error':
                handlers.onError?.(event.message)
                break
            }
          } catch (e) {
            console.warn('[SSE] 解析失败:', block, e)
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        handlers.onError?.(err.message)
      }
    })

  // 返回取消函数
  return () => controller.abort()
}