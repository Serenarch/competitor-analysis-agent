<template>
  <div class="home-container">
    <div class="page-header">
      <h1>🔍 智能竞品分析助手 Agent</h1>
      <p>输入分析对象，自动完成多维度调研与报告生成</p>
    </div>

    <a-card class="form-card">
      <div class="history-link">
        <a-button type="link" @click="goHistory">
          📚 查看历史报告
        </a-button>
      </div>
      <a-form :model="form" layout="vertical" @finish="handleSubmit">
        <!-- 领域选择 -->
        <a-form-item label="分析对象类型" name="domain">
          <a-radio-group v-model:value="form.domain" button-style="solid">
            <a-radio-button value="software">💻 软件/SaaS</a-radio-button>
            <a-radio-button value="product">📦 实体商品</a-radio-button>
            <a-radio-button value="service">🎓 服务</a-radio-button>
          </a-radio-group>
          <div class="domain-hint">{{ domainHint }}</div>
        </a-form-item>

        <!-- 分析对象：单/多输入 -->
        <a-form-item
          :label="domainConfig.objectLabel"
          name="competitorsInput"
          :rules="[{ required: true, message: `请输入${domainConfig.objectLabel}` }]"
        >
          <a-textarea
            v-model:value="form.competitorsInput"
            :placeholder="domainConfig.placeholder"
            :auto-size="{ minRows: 1, maxRows: 3 }"
            allow-clear
          />
          <div class="input-hint">
            💡 多个对象用逗号分隔（如：Notion, Figma, Linear），系统将自动对比分析
          </div>
        </a-form-item>

        <!-- 对比模式开关 -->
        <a-form-item v-if="parsedCompetitors.length > 1" label="分析模式">
          <a-switch v-model:checked="form.comparison_mode" />
          <span class="mode-hint">
            {{ form.comparison_mode
              ? '对比模式：生成横向对比报告'
              : '独立模式：依次分析每个对象' }}
          </span>
        </a-form-item>

        <!-- 行业 -->
        <a-form-item label="所属行业" name="industry">
          <a-input
            v-model:value="form.industry"
            :placeholder="domainConfig.industryPlaceholder"
            size="large"
            allow-clear
          />
        </a-form-item>

        <!-- 分析维度 -->
        <a-form-item label="分析维度" name="focus_areas">
          <a-checkbox-group v-model:value="form.focus_areas">
            <a-checkbox
              v-for="area in domainConfig.focusAreas"
              :key="area"
              :value="area"
            >
              {{ area }}
            </a-checkbox>
          </a-checkbox-group>
        </a-form-item>

        <a-form-item>
          <a-button type="primary" html-type="submit" size="large" block>
            {{ parsedCompetitors.length > 1 && form.comparison_mode
              ? '开始对比分析'
              : '开始分析' }}
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'

const router = useRouter()

const DOMAIN_CONFIG = {
  software: {
    objectLabel: '竞品名称',
    placeholder: '如：Notion、Figma、Linear\n（多个用逗号分隔）',
    industryPlaceholder: '如：生产力工具、设计工具',
    focusAreas: ['产品定位', '核心功能', '定价策略', '用户评价', '竞争格局'],
    hint: '适合分析 SaaS 产品、App、开发工具等软件类产品',
  },
  product: {
    objectLabel: '商品名称',
    placeholder: '如：Sony WH-1000XM5、iPhone 16 Pro\n（多个用逗号分隔）',
    industryPlaceholder: '如：无线降噪耳机、智能手机',
    focusAreas: ['产品参数', '价格区间', '用户口碑', '销售渠道', '品牌定位'],
    hint: '适合分析数码、家电、日用品等实体商品',
  },
  service: {
    objectLabel: '服务名称',
    placeholder: '如：Coursera Plus、极客时间\n（多个用逗号分隔）',
    industryPlaceholder: '如：在线教育、咨询服务',
    focusAreas: ['服务内容', '收费模式', '客户反馈', '服务范围', '服务质量'],
    hint: '适合分析课程、订阅服务、咨询等服务类产品',
  },
}
const goHistory = () => router.push({ name: 'history' })

const form = reactive({
  domain: 'software',
  competitorsInput: '',
  comparison_mode: true,   // 默认开启对比模式
  industry: '',
  focus_areas: [...DOMAIN_CONFIG.software.focusAreas],
})

// 解析输入框内容为数组
const parsedCompetitors = computed(() => {
  return form.competitorsInput
    .split(/[,，\n]/)
    .map((s) => s.trim())
    .filter(Boolean)
})

const domainConfig = computed(() => {
  const config = DOMAIN_CONFIG[form.domain as keyof typeof DOMAIN_CONFIG]
  return {
    objectLabel: config.objectLabel,
    placeholder: config.placeholder,
    industryPlaceholder: config.industryPlaceholder,
    focusAreas: config.focusAreas,
  }
})

const domainHint = computed(() => {
  return DOMAIN_CONFIG[form.domain as keyof typeof DOMAIN_CONFIG].hint
})

watch(() => form.domain, (newDomain) => {
  form.focus_areas = [...DOMAIN_CONFIG[newDomain as keyof typeof DOMAIN_CONFIG].focusAreas]
})

const handleSubmit = () => {
  const competitors = parsedCompetitors.value
  if (competitors.length === 0) {
    message.warning(`请输入${domainConfig.value.objectLabel}`)
    return
  }

  const isComparison = competitors.length > 1 && form.comparison_mode

  router.push({
    name: 'analysis',
    query: {
      competitors: competitors.join(','),
      industry: form.industry.trim(),
      domain: form.domain,
      focus_areas: form.focus_areas.join(','),
      comparison_mode: isComparison ? '1' : '0',
    },
  })
}
</script>

<style scoped>
.home-container {
  max-width: 720px;
  margin: 0 auto;
  padding: 60px 20px;
}
.page-header {
  text-align: center;
  margin-bottom: 40px;
}
.page-header h1 {
  font-size: 32px;
  margin-bottom: 12px;
}
.page-header p {
  color: #666;
  font-size: 16px;
}
.form-card {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.domain-hint,
.input-hint {
  margin-top: 8px;
  font-size: 13px;
  color: #999;
  line-height: 1.6;
}
.history-link {
  text-align: center;
  margin-top: 16px;
}
.mode-hint {
  margin-left: 12px;
  color: #666;
  font-size: 13px;
}
</style>