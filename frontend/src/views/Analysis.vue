<template>
  <div class="analysis-container">
    <div class="page-header">
      <h1>🔍 正在分析：{{ title }}</h1>
      <p v-if="industry">行业：{{ industry }}</p>
      <div class="tag-row">
        <span class="domain-tag">{{ domainLabel }}</span>
        <span v-if="comparisonMode" class="mode-tag">对比模式</span>
      </div>
    </div>

    <!-- 进度条 -->
    <a-card class="progress-card">
      <div class="progress-header">
        <span class="progress-status">{{ currentStatus }}</span>
        <span class="progress-percent">{{ progressPercent }}%</span>
      </div>
      <a-progress
        :percent="progressPercent"
        :status="progressStatus"
        :show-info="false"
        stroke-color="#1677ff"
      />
      <div class="progress-hint" v-if="duration > 0">
        已用时 {{ duration.toFixed(0) }} 秒
      </div>
    </a-card>

    <!-- 任务列表（按竞品分组） -->
    <a-card class="tasks-card" :title="`📋 分析任务（${currentCompetitor || '准备中'}）`">
      <a-empty v-if="tasks.length === 0" description="正在规划任务..." />
      <div v-else class="task-list">
        <div
          v-for="task in tasks"
          :key="task.id"
          :class="['task-item', task.status]"
        >
          <div class="task-icon">
            <loading-outlined v-if="task.status === 'running'" spin />
            <check-circle-outlined
              v-else-if="task.status === 'completed'"
              style="color: #52c41a"
            />
            <clock-circle-outlined v-else style="color: #999" />
          </div>
          <div class="task-info">
            <div class="task-title">{{ task.id }}. {{ task.title }}</div>
            <div class="task-intent">{{ task.intent }}</div>
          </div>
          <div class="task-status">
            <a-tag v-if="task.status === 'completed'" color="success">已完成</a-tag>
            <a-tag v-else-if="task.status === 'running'" color="processing">分析中</a-tag>
            <a-tag v-else color="default">等待中</a-tag>
          </div>
        </div>
      </div>
    </a-card>

    <!-- 实时日志 -->
    <a-card class="logs-card" title="📊 实时日志">
      <div class="log-list" ref="logListRef">
        <div
          v-for="(log, idx) in logs"
          :key="idx"
          :class="['log-item', log.level]"
        >
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.message }}</span>
        </div>
        <a-empty v-if="logs.length === 0" description="等待中..." />
      </div>
    </a-card>

    <a-alert
      v-if="errorMessage"
      type="error"
      :message="errorMessage"
      show-icon
      class="error-alert"
    />

    <div class="actions">
      <a-button @click="handleCancel" danger v-if="!isDone">取消分析</a-button>
      <a-button @click="goHome">返回首页</a-button>
      <a-button v-if="isDone && reportId" type="primary" @click="goReport">
        查看完整报告
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  LoadingOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons-vue'
import { streamAnalysis } from '@/services/api'
import type { TodoItem } from '@/types'

const route = useRoute()
const router = useRouter()

// ============================================================
// URL 参数
// ============================================================
const competitors = ((route.query.competitors as string) || '').split(',').filter(Boolean)
const industry = (route.query.industry as string) || ''
const domain = (route.query.domain as string) || 'software'
const comparisonMode = route.query.comparison_mode === '1'
const focusAreas = ((route.query.focus_areas as string) || '').split(',').filter(Boolean)

const title = competitors.length > 1 ? competitors.join(' vs ') : (competitors[0] || '')

const domainLabel = computed(() => {
  const map: Record<string, string> = {
    software: '💻 软件产品',
    product: '📦 实体商品',
    service: '🎓 服务',
  }
  return map[domain] || '💻 软件产品'
})

// ============================================================
// 状态
// ============================================================
const tasks = ref<TodoItem[]>([])
const currentCompetitor = ref('')   // 当前处理的竞品
const logs = ref<Array<{ time: string; message: string; level: string }>>([])
const currentStatus = ref('准备中...')
const progressPercent = ref(0)
const duration = ref(0)
const reportId = ref('')
const errorMessage = ref('')
const isDone = ref(false)
const logListRef = ref<HTMLElement>()

let cancelStream: (() => void) | null = null
let timer: number | null = null

const progressStatus = computed(() => {
  if (errorMessage.value) return 'exception'
  if (isDone.value) return 'success'
  return 'active'
})

// ============================================================
// 工具
// ============================================================
const addLog = (msg: string, level = 'info') => {
  const now = new Date()
  const time = `${now.getHours().toString().padStart(2, '0')}:${now
    .getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
  logs.value.push({ time, message: msg, level })
  setTimeout(() => {
    if (logListRef.value) {
      logListRef.value.scrollTop = logListRef.value.scrollHeight
    }
  }, 50)
}

const updateTaskStatus = (taskId: number, status: TodoItem['status']) => {
  const task = tasks.value.find((t) => t.id === taskId)
  if (task) task.status = status
}

// ============================================================
// 启动
// ============================================================
const startStream = () => {
  addLog(`开始分析：${title}（${domainLabel.value}）`)
  if (comparisonMode) addLog('📊 对比模式已开启')
  currentStatus.value = '正在规划任务...'
  progressPercent.value = 5

  cancelStream = streamAnalysis(
    {
      competitors,
      industry: industry || undefined,
      domain,
      focus_areas: focusAreas.length > 0 ? focusAreas : undefined,
    },
    {
      onStart: (data) => {
        reportId.value = data.report_id
        addLog(`任务已启动，report_id=${data.report_id}`)
        if (data.competitors && data.competitors.length > 0) {
          currentCompetitor.value = data.competitors[0]
        }
      },

      onTasks: (newTasks) => {
        tasks.value = newTasks.map((t) => ({ ...t, status: 'pending' }))
        addLog(`规划完成，共 ${newTasks.length} 个子任务`, 'success')
        progressPercent.value = 10
      },

      onStatus: (msg) => {
        currentStatus.value = msg
        addLog(msg)

        // 检测到切换竞品
        const switchMatch = msg.match(/切换到.*：(.+?)（/)
        if (switchMatch) {
          currentCompetitor.value = switchMatch[1]
          tasks.value = []
        }

        if (msg.includes('采集')) {
          progressPercent.value = Math.min(progressPercent.value + 2, 80)
          const nextTask = tasks.value.find((t) => t.status === 'pending')
          if (nextTask) updateTaskStatus(nextTask.id, 'running')
        } else if (msg.includes('对比分析')) {
          progressPercent.value = 90
        } else if (msg.includes('报告')) {
          progressPercent.value = 95
        }
      },

      onSummary: (data) => {
        updateTaskStatus(data.task_id, 'completed')
        const comp = data.competitor ? `[${data.competitor}] ` : ''
        addLog(
          `✅ ${comp}任务 ${data.task_id} 完成：${data.title}（${data.summary.length} 字）`,
          'success'
        )
      },

      onReport: (report) => {
        addLog(`📄 报告生成完成，共 ${report.length} 字`, 'success')
        progressPercent.value = 98
        currentStatus.value = '报告生成完成'
      },

      onDone: (data) => {
        isDone.value = true
        progressPercent.value = 100
        currentStatus.value = '分析完成'
        addLog(`🎉 全部完成，总耗时 ${data.duration_seconds} 秒`, 'success')
        message.success('分析完成！')
      },

      onError: (err) => {
        errorMessage.value = err
        addLog(`❌ 错误：${err}`, 'error')
        currentStatus.value = '分析失败'
        message.error('分析失败：' + err)
      },
    }
  )
}

const startTimer = () => {
  timer = window.setInterval(() => {
    if (!isDone.value && !errorMessage.value) {
      duration.value += 1
    }
  }, 1000)
}

const handleCancel = () => {
  if (cancelStream) {
    cancelStream()
    addLog('用户取消了分析', 'warning')
  }
  router.push({ name: 'home' })
}

const goHome = () => router.push({ name: 'home' })

const goReport = () => {
  if (reportId.value) {
    router.push({ name: 'report', params: { id: reportId.value } })
  }
}

onMounted(() => {
  if (competitors.length === 0) {
    message.error('缺少分析对象名称')
    router.push({ name: 'home' })
    return
  }
  startTimer()
  startStream()
})

onUnmounted(() => {
  if (cancelStream) cancelStream()
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.analysis-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px;
}
.page-header {
  text-align: center;
  margin-bottom: 24px;
}
.page-header h1 {
  font-size: 28px;
  margin-bottom: 8px;
}
.page-header p {
  color: #666;
}
.tag-row {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
}
.domain-tag,
.mode-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
}
.domain-tag {
  background: #e6f4ff;
  color: #1677ff;
}
.mode-tag {
  background: #fff7e6;
  color: #fa8c16;
}
.progress-card,
.tasks-card,
.logs-card {
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}
.progress-status {
  font-weight: 500;
  color: #1677ff;
}
.progress-percent {
  color: #666;
}
.progress-hint {
  margin-top: 8px;
  color: #999;
  font-size: 13px;
  text-align: right;
}
.task-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  background: #fafafa;
  transition: all 0.3s;
}
.task-item.running {
  background: #e6f4ff;
  border-left: 3px solid #1677ff;
}
.task-item.completed {
  background: #f6ffed;
  border-left: 3px solid #52c41a;
}
.task-icon {
  font-size: 18px;
}
.task-info {
  flex: 1;
}
.task-title {
  font-weight: 500;
  margin-bottom: 4px;
}
.task-intent {
  font-size: 13px;
  color: #666;
}
.log-list {
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 6px;
  padding: 12px;
  min-height: 100px;
}
.log-item {
  padding: 4px 0;
  display: flex;
  gap: 8px;
}
.log-time {
  color: #858585;
  flex-shrink: 0;
}
.log-item.success .log-msg {
  color: #4ec9b0;
}
.log-item.error .log-msg {
  color: #f48771;
}
.log-item.warning .log-msg {
  color: #dcdaa;
}
.error-alert {
  margin-bottom: 20px;
}
.actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
}
</style>