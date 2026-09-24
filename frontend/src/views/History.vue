<template>
  <div class="history-container">
    <div class="page-header">
      <h1>📚 历史报告</h1>
      <p>查看之前生成的所有竞品分析报告</p>
    </div>

    <a-card class="list-card">
      <a-spin :spinning="loading">
        <a-empty
          v-if="!loading && items.length === 0"
          description="暂无历史报告"
        />

        <a-list v-else :data-source="items" item-layout="horizontal">
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta>
                <template #title>
                  <span class="report-title">{{ item.competitor }}</span>
                  <a-tag
                    v-if="item.industry"
                    color="blue"
                    style="margin-left: 8px"
                  >
                    {{ item.industry }}
                  </a-tag>
                  <a-tag
                    :color="item.status === 'completed' ? 'success' : 'default'"
                    style="margin-left: 8px"
                  >
                    {{ item.status === 'completed' ? '已完成' : item.status }}
                  </a-tag>
                </template>
                <template #description>
                  <span>生成时间：{{ formatTime(item.created_at) }}</span>
                  <span style="margin-left: 16px; color: #999;">
                    ID: {{ item.report_id }}
                  </span>
                </template>
              </a-list-item-meta>

              <template #actions>
                <a-button type="link" @click="goReport(item.report_id)">
                  查看
                </a-button>
                <a-popconfirm
                  title="确定删除这份报告？删除后不可恢复。"
                  ok-text="确定"
                  cancel-text="取消"
                  @confirm="handleDelete(item.report_id)"
                >
                  <a-button type="link" danger>删除</a-button>
                </a-popconfirm>
              </template>
            </a-list-item>
          </template>
        </a-list>
      </a-spin>
    </a-card>

    <div class="actions">
      <a-button @click="goHome">返回首页</a-button>
      <a-button type="primary" :loading="loading" @click="loadHistory">
        刷新
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { getHistory, deleteHistory } from '@/services/api'
import type { HistoryItem } from '@/types'

const router = useRouter()
const items = ref<HistoryItem[]>([])
const loading = ref(false)

const loadHistory = async () => {
  loading.value = true
  try {
    const res = await getHistory(50)
    items.value = res.items || []
  } catch (e: any) {
    message.error('加载历史失败：' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const handleDelete = async (reportId: string) => {
  try {
    await deleteHistory(reportId)
    message.success('删除成功')
    await loadHistory()
  } catch (e: any) {
    message.error('删除失败：' + (e.message || '未知错误'))
  }
}

const formatTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

const goHome = () => router.push({ name: 'home' })
const goReport = (id: string) =>
  router.push({ name: 'report', params: { id } })

onMounted(loadHistory)
</script>

<style scoped>
.history-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px;
}
.page-header {
  text-align: center;
  margin-bottom: 32px;
}
.page-header h1 {
  font-size: 28px;
  margin-bottom: 8px;
}
.page-header p {
  color: #666;
}
.list-card {
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.report-title {
  font-weight: 500;
  font-size: 15px;
}
.actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>