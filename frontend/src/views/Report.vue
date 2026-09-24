<template>
  <div class="report-container">
    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <a-spin size="large" />
      <p>加载报告中...</p>
    </div>

    <!-- 加载失败 -->
    <a-result
      v-else-if="error"
      status="error"
      title="加载失败"
      :sub-title="error"
    >
      <template #extra>
        <a-button type="primary" @click="goHome">返回首页</a-button>
      </template>
    </a-result>

    <!-- 报告内容 -->
    <div v-else-if="report" class="report-content">
      <!-- 顶部操作栏 -->
      <div class="report-header">
        <div class="header-info">
          <h1>{{ reportTitle }}</h1>
          <div class="meta">
            <span v-if="report.industry">行业：{{ report.industry }}</span>
            <span v-if="isComparison" class="mode-badge">对比分析</span>
            <span>生成时间：{{ formatTime(report.created_at) }}</span>
            <span>耗时：{{ report.duration_seconds.toFixed(0) }} 秒</span>
            <span>来源：{{ uniqueSources.length }} 个</span>
          </div>
        </div>
        <div class="header-actions">
          <a-button @click="goHome">返回首页</a-button>
          <a-button @click="exportMarkdown">导出 Markdown</a-button>
          <a-button type="primary" @click="exportPDF" :loading="pdfLoading">
            导出 PDF
          </a-button>
        </div>
      </div>

      <!-- ==================== 对比模式：对比矩阵 ==================== -->
      <a-card
        v-if="isComparison && hasMatrix"
        title="📊 对比矩阵"
        class="matrix-card"
      >
        <div
          v-for="(compData, dimension) in report.comparison_matrix"
          :key="dimension"
          class="matrix-row"
        >
          <h4 class="matrix-dimension">{{ dimension }}</h4>
          <table class="matrix-table">
            <thead>
              <tr>
                <th
                  v-for="comp in report.competitors"
                  :key="comp"
                  class="matrix-th"
                >
                  {{ comp }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td
                  v-for="comp in report.competitors"
                  :key="comp"
                  class="matrix-td"
                >
                  {{ compData[comp] || '未找到' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </a-card>

      <!-- ==================== 对比模式：对比洞察 ==================== -->
      <a-card
        v-if="isComparison && report.comparison_insights"
        title="💡 对比洞察"
        class="insights-card"
      >
        <p class="insights-text">{{ report.comparison_insights }}</p>
      </a-card>

      <!-- 主体：左报告 + 右侧导航 -->
      <div class="report-body">
        <!-- 左侧：报告 Markdown -->
        <div class="report-main">
          <a-card>
            <div
              class="markdown-body"
              v-html="renderedReport"
              ref="reportContentRef"
            ></div>
          </a-card>
        </div>

        <!-- 右侧：快捷导航 + 来源 -->
        <div class="report-aside">
          <a-card title="📑 快捷导航" size="small">
            <div class="nav-list">
              <div
                v-for="section in sections"
                :key="section.id"
                class="nav-item"
                @click="scrollTo(section.id)"
              >
                {{ section.title }}
              </div>
            </div>
          </a-card>
          <a-card title="📎 信息来源" size="small" style="margin-top: 16px;">
            <div class="source-list">
              <div
                v-for="(src, idx) in uniqueSources"
                :key="idx"
                class="source-item"
              >
                <div class="source-title">
                  <a :href="src.url" target="_blank" rel="noopener">
                    {{ src.title }}
                  </a>
                </div>
                <div class="source-url">{{ src.url }}</div>
              </div>
            </div>
          </a-card>
        </div>
      </div>

      <!-- ==================== 子任务分析（可折叠） ==================== -->
      <a-card
        class="summaries-card"
        :title="`🔍 各子任务分析（${uniqueSummaries.length} 条）`"
        style="margin-top: 20px;"
      >
        <a-collapse v-model:activeKey="activeSummaryKeys" ghost>
          <a-collapse-panel
            v-for="s in uniqueSummaries"
            :key="summaryKey(s)"
            :header="summaryHeader(s)"
          >
            <div
              class="summary-content"
              v-html="renderMarkdown(s.summary)"
            ></div>
            <div v-if="s.sources && s.sources.length" class="summary-sources">
              <div class="sources-label">来源：</div>
              <div
                v-for="(src, i) in s.sources"
                :key="i"
                class="source-link"
              >
                [{{ i + 1 }}]
                <a :href="src.url" target="_blank" rel="noopener">
                  {{ src.title }}
                </a>
              </div>
            </div>
          </a-collapse-panel>
        </a-collapse>
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { marked } from 'marked'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import { getReport } from '@/services/api'
import type { ReportDetail, SourceItem, TaskSummary } from '@/types'

const route = useRoute()
const router = useRouter()
const reportId = route.params.id as string

const report = ref<ReportDetail | null>(null)
const loading = ref(true)
const error = ref('')
const pdfLoading = ref(false)
const reportContentRef = ref<HTMLElement>()
const activeSummaryKeys = ref<string[]>([])

// ============================================================
// 配置 marked
// ============================================================
marked.setOptions({
  breaks: true,
  gfm: true,
})

// ============================================================
// 判断是否为对比模式
// ============================================================
const isComparison = computed(() => {
  if (!report.value) return false
  return (
    report.value.report_type === 'comparison' ||
    report.value.comparison_mode === true
  )
})

// 报告标题
const reportTitle = computed(() => {
  if (!report.value) return ''
  if (isComparison.value && report.value.competitors?.length > 1) {
    return report.value.competitors.join(' vs ') + ' 对比分析'
  }
  return report.value.competitor + ' 分析报告'
})

// 是否有对比矩阵
const hasMatrix = computed(() => {
  if (!report.value?.comparison_matrix) return false
  return Object.keys(report.value.comparison_matrix).length > 0
})

// ============================================================
// Markdown 渲染
// ============================================================
const renderedReport = computed(() => {
  if (!report.value) return ''
  return marked(report.value.report || '') as string
})

const renderMarkdown = (text: string) => marked(text) as string

// ============================================================
// 提取章节（右侧导航）
// ============================================================
const sections = computed(() => {
  if (!report.value) return []
  const regex = /^#{1,2}\s+(.+)$/gm
  const result: Array<{ id: string; title: string }> = []
  let match
  while ((match = regex.exec(report.value.report)) !== null) {
    const title = match[1].trim()
    const id = 'section-' + title.replace(/[\s\.、，,]+/g, '-')
    result.push({ id, title })
  }
  return result
})

// ============================================================
// 去重来源
// ============================================================
const uniqueSources = computed(() => {
  if (!report.value) return []
  const seen = new Set()
  const result: SourceItem[] = []
  for (const s of report.value.all_sources || []) {
    if (s.url && !seen.has(s.url)) {
      seen.add(s.url)
      result.push(s)
    }
  }
  return result
})

// ============================================================
// 去重 summaries（按 competitor + task_id 保留最新）
// ============================================================
const uniqueSummaries = computed(() => {
  if (!report.value) return []
  const map = new Map<string, TaskSummary>()
  for (const s of report.value.summaries || []) {
    const key = `${s.competitor || ''}__${s.task_id}`
    map.set(key, s)
  }
  return Array.from(map.values()).sort((a, b) => {
    if (a.competitor !== b.competitor) {
      return (a.competitor || '').localeCompare(b.competitor || '')
    }
    return a.task_id - b.task_id
  })
})

const summaryKey = (s: TaskSummary) => `${s.competitor || ''}__${s.task_id}`

const summaryHeader = (s: TaskSummary) => {
  const compPrefix =
    isComparison.value && s.competitor ? `[${s.competitor}] ` : ''
  return `${compPrefix}${s.task_id}. ${s.title}`
}

// ============================================================
// 工具函数
// ============================================================
const formatTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

const scrollTo = (id: string) => {
  nextTick(() => {
    const headings = reportContentRef.value?.querySelectorAll('h1, h2')
    headings?.forEach((h) => {
      const text = h.textContent?.trim() || ''
      const hid = 'section-' + text.replace(/[\s\.、，,]+/g, '-')
      if (hid === id) {
        h.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    })
  })
}

// ============================================================
// 导出 Markdown
// ============================================================
const exportMarkdown = () => {
  if (!report.value) return
  const blob = new Blob([report.value.report], {
    type: 'text/markdown;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const filename = isComparison.value
    ? `${report.value.competitors.join('_vs_')}_对比分析_${reportId}.md`
    : `${report.value.competitor}_分析_${reportId}.md`
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
  message.success('Markdown 导出成功')
}

// ============================================================
// 导出 PDF
// ============================================================
const exportPDF = async () => {
  if (!report.value) return
  pdfLoading.value = true
  const hideMsg = message.loading('正在生成 PDF，请稍候...', 0)

  try {
    // 找到报告主体（markdown-body 的父卡片）
    const markdownEl = reportContentRef.value
    if (!markdownEl) {
      message.error('找不到报告内容')
      return
    }

    // 截图（scale 2 保证清晰度）
    const canvas = await html2canvas(markdownEl, {
      scale: 2,
      useCORS: true,
      backgroundColor: '#ffffff',
      logging: false,
    })

    const pdf = new jsPDF('p', 'mm', 'a4')
    const pageWidth = pdf.internal.pageSize.getWidth()
    const pageHeight = pdf.internal.pageSize.getHeight()
    const margin = 10
    const imgWidth = pageWidth - margin * 2
    const imgHeight = (canvas.height * imgWidth) / canvas.width

    const imgData = canvas.toDataURL('image/jpeg', 0.92)

    // 单页能放下
    if (imgHeight <= pageHeight - margin * 2) {
      pdf.addImage(imgData, 'JPEG', margin, margin, imgWidth, imgHeight)
    } else {
      // 分页：逐页计算 canvas 的裁剪区域
      const pageContentHeight = pageHeight - margin * 2 // 每页可用的图片高度（mm）
      const totalPages = Math.ceil(imgHeight / pageContentHeight)
      const pxPerMm = canvas.width / imgWidth

      for (let page = 0; page < totalPages; page++) {
        if (page > 0) pdf.addPage()

        // 计算当前页在 canvas 中的 y 起点（px）
        const yStartMm = page * pageContentHeight
        const yStartPx = Math.floor(yStartMm * pxPerMm)
        // 当前页在 canvas 中占用的高度（px）
        const pageHeightPx = Math.min(
          Math.floor(pageContentHeight * pxPerMm),
          canvas.height - yStartPx
        )

        // 创建一个临时 canvas 截取当前页
        const pageCanvas = document.createElement('canvas')
        pageCanvas.width = canvas.width
        pageCanvas.height = pageHeightPx
        const ctx = pageCanvas.getContext('2d')
        if (!ctx) continue
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height)
        ctx.drawImage(
          canvas,
          0,
          yStartPx,
          canvas.width,
          pageHeightPx,
          0,
          0,
          canvas.width,
          pageHeightPx
        )

        const pageImgData = pageCanvas.toDataURL('image/jpeg', 0.92)
        const pageImgHeightMm = (pageHeightPx * imgWidth) / canvas.width
        pdf.addImage(
          pageImgData,
          'JPEG',
          margin,
          margin,
          imgWidth,
          pageImgHeightMm
        )
      }
    }

    // 文件名
    const filename = isComparison.value
      ? `${report.value.competitors.join('_vs_')}_对比分析_${reportId}.pdf`
      : `${report.value.competitor}_分析_${reportId}.pdf`
    pdf.save(filename)
    message.success('PDF 导出成功')
  } catch (e: any) {
    console.error(e)
    message.error('PDF 导出失败：' + (e.message || '未知错误'))
  } finally {
    pdfLoading.value = false
    hideMsg()
  }
}

// ============================================================
// 生命周期
// ============================================================
const goHome = () => router.push({ name: 'home' })

onMounted(async () => {
  if (!reportId) {
    error.value = '缺少报告 ID'
    loading.value = false
    return
  }
  try {
    report.value = await getReport(reportId)
    if (uniqueSummaries.value.length > 0) {
      activeSummaryKeys.value = [summaryKey(uniqueSummaries.value[0])]
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || '加载报告失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.report-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 24px;
}

.loading-state {
  text-align: center;
  padding: 100px 0;
}
.loading-state p {
  margin-top: 16px;
  color: #666;
}

/* ==================== 报告头部 ==================== */
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 2px solid #f0f0f0;
}
.header-info h1 {
  font-size: 26px;
  margin-bottom: 12px;
}
.meta {
  display: flex;
  gap: 16px;
  color: #666;
  font-size: 13px;
  flex-wrap: wrap;
  align-items: center;
}
.mode-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #fff7e6;
  color: #fa8c16;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* ==================== 对比矩阵 ==================== */
.matrix-card,
.insights-card {
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.matrix-row {
  margin-bottom: 24px;
}
.matrix-row:last-child {
  margin-bottom: 0;
}
.matrix-dimension {
  margin-bottom: 10px;
  color: #1677ff;
  font-size: 15px;
}
.matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  border: 1px solid #e8e8e8;
}
.matrix-th,
.matrix-td {
  border: 1px solid #e8e8e8;
  padding: 10px 14px;
  text-align: left;
  vertical-align: top;
  line-height: 1.6;
}
.matrix-th {
  background: #fafafa;
  font-weight: 600;
  color: #333;
}
.matrix-td {
  color: #555;
}

/* ==================== 对比洞察 ==================== */
.insights-text {
  line-height: 1.9;
  color: #333;
  font-size: 14px;
  margin: 0;
  white-space: pre-wrap;
}

/* ==================== 主体布局 ==================== */
.report-body {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
}
@media (max-width: 1024px) {
  .report-body {
    grid-template-columns: 1fr;
  }
  .report-aside {
    display: none;
  }
}

/* ==================== 右侧导航 ==================== */
.nav-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.nav-item {
  padding: 6px 10px;
  cursor: pointer;
  border-radius: 4px;
  color: #555;
  font-size: 13px;
  transition: all 0.2s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nav-item:hover {
  background: #f0f5ff;
  color: #1677ff;
}

/* ==================== 来源列表 ==================== */
.source-list {
  max-height: 400px;
  overflow-y: auto;
}
.source-item {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 12px;
}
.source-item:last-child {
  border-bottom: none;
}
.source-title a {
  color: #1677ff;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.source-url {
  color: #999;
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}

/* ==================== 子任务分析 ==================== */
.summary-content {
  padding: 8px 0;
  line-height: 1.8;
}
.summary-sources {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px dashed #eee;
}
.sources-label {
  font-weight: 500;
  margin-bottom: 8px;
  color: #666;
}
.source-link {
  font-size: 13px;
  padding: 3px 0;
}

/* ==================== Markdown 样式 ==================== */
.markdown-body {
  line-height: 1.8;
  color: #333;
}
.markdown-body :deep(h1) {
  font-size: 26px;
  margin: 24px 0 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid #f0f0f0;
}
.markdown-body :deep(h2) {
  font-size: 20px;
  margin: 28px 0 14px;
  padding-left: 12px;
  border-left: 4px solid #1677ff;
}
.markdown-body :deep(h3) {
  font-size: 16px;
  margin: 20px 0 10px;
}
.markdown-body :deep(p) {
  margin: 10px 0;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 24px;
  margin: 10px 0;
}
.markdown-body :deep(li) {
  margin: 4px 0;
}
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e8e8e8;
  padding: 8px 12px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: #fafafa;
  font-weight: 600;
}
.markdown-body :deep(code) {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
  color: #c7254e;
}
.markdown-body :deep(strong) {
  color: #000;
}
.markdown-body :deep(blockquote) {
  border-left: 4px solid #e8e8e8;
  padding-left: 12px;
  color: #666;
  margin: 12px 0;
  background: #fafafa;
}
</style>