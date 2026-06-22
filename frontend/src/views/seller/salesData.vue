<template>
  <div class="sales-data-container">
    <!-- AI 运营洞察 -->
    <el-card class="insight-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="insight-title">
            <span>AI 运营洞察</span>
            <el-tag v-if="insightMeta.source" :type="sourceTagType" size="small">
              {{ insightMeta.source === 'openai' ? 'OpenAI' : 'Fallback' }}
            </el-tag>
          </div>
          <span class="insight-meta" v-if="insightMeta.generatedAt">
            {{ insightMeta.windowDays }} 天分析 · {{ insightMeta.generatedAt }}
          </span>
        </div>
      </template>

      <el-skeleton v-if="insightLoading" :rows="4" animated />
      <el-alert
        v-else-if="insightError"
        type="warning"
        :title="insightError"
        show-icon
        :closable="false"
      />
      <el-empty
        v-else-if="!insightBriefing && !insightCards.length"
        description="暂无足够数据生成运营洞察"
      />
      <div v-else class="insight-content">
        <div class="briefing-box">
          {{ insightBriefing }}
        </div>
        <el-row :gutter="16" class="action-card-row">
          <el-col
            v-for="card in insightCards"
            :key="`${card.metric}-${card.title}`"
            :xs="24"
            :sm="12"
            :lg="8"
          >
            <el-card class="action-card" shadow="never">
              <div class="action-card-header">
                <span>{{ card.title }}</span>
                <el-tag :type="priorityTagType(card.priority)" size="small">
                  {{ priorityText(card.priority) }}
                </el-tag>
              </div>
              <p class="recommendation">{{ card.recommendation }}</p>
              <p class="reason">{{ card.reason }}</p>
              <div class="evidence-list">
                <el-tag
                  v-for="item in card.evidence"
                  :key="item"
                  class="evidence-tag"
                  size="small"
                  effect="plain"
                >
                  {{ item }}
                </el-tag>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>

    <!-- 当日销售数据卡片 -->
    <el-row :gutter="20" class="today-stats">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>Today's Sales</span>
            </div>
          </template>
          <div class="card-content">
            <span class="amount">¥{{ todayData.total_sales.toFixed(2) }}</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>Today's Orders</span>
            </div>
          </template>
          <div class="card-content">
            <span class="amount">{{ todayData.order_count }}</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>Today's Sales Quantity</span>
            </div>
          </template>
          <div class="card-content">
            <span class="amount">{{ todayData.total_quantity }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 历史销售数据图表 -->
    <el-card class="chart-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>Historical Sales Trends</span>
          <el-select v-model="timeRange" @change="handleTimeRangeChange" style="width: 120px">
            <el-option label="Last 7 Days" value="7" />
            <el-option label="Last 30 Days" value="30" />
            <el-option label="Last 90 Days" value="90" />
          </el-select>
        </div>
      </template>
      <div class="chart-container">
        <div ref="salesChart" style="width: 100%; height: 400px"></div>
      </div>
    </el-card>

    <!-- 热销商品列表 -->
    <el-card class="top-products" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>Top 5 Best-Selling Products</span>
        </div>
      </template>
      <el-table :data="topProducts" style="width: 100%">
        <el-table-column prop="productName" label="Product Name" />
        <el-table-column prop="imageUrl" label="Product Image" width="100">
          <template #default="scope">
            <el-image 
              :src="scope.row.imageUrl" 
              :preview-src-list="[scope.row.imageUrl]"
              fit="cover"
              style="width: 50px; height: 50px"
            />
          </template>
        </el-table-column>
        <el-table-column prop="totalSold" label="Sales Quantity" />
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted, reactive, computed } from 'vue'
import { getSalesData, getSellerInsights } from '@/api/seller'
import * as echarts from 'echarts'

export default {
  name: 'SalesData',
  setup() {
    const timeRange = ref('30')
    const salesChart = ref(null)
    const chart = ref(null)
    
    const todayData = reactive({
      total_sales: 0,
      order_count: 0,
      total_quantity: 0
    })
    
    const topProducts = ref([])
    const historyData = ref([])
    const insightLoading = ref(false)
    const insightError = ref('')
    const insightBriefing = ref('')
    const insightCards = ref([])
    const insightMeta = reactive({
      source: '',
      generatedAt: '',
      windowDays: 30
    })

    const sourceTagType = computed(() => insightMeta.source === 'openai' ? 'success' : 'info')

    const priorityTagType = priority => {
      if (priority === 'high') return 'danger'
      if (priority === 'medium') return 'warning'
      return 'info'
    }

    const priorityText = priority => {
      if (priority === 'high') return '高优先级'
      if (priority === 'medium') return '中优先级'
      return '低优先级'
    }

    // 初始化图表
    const initChart = () => {
      if (salesChart.value) {
        chart.value = echarts.init(salesChart.value)
      }
    }

    // 更新图表数据
    const updateChart = () => {
      if (!chart.value) return

      const dates = historyData.value.map(item => item.date)
      const sales = historyData.value.map(item => item.total_sales)
      const orders = historyData.value.map(item => item.order_count)

      const option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          }
        },
        legend: {
          data: ['销售额', '订单数']
        },
        xAxis: {
          type: 'category',
          data: dates
        },
        yAxis: [
          {
            type: 'value',
            name: '销售额',
            axisLabel: {
              formatter: '¥{value}'
            }
          },
          {
            type: 'value',
            name: '订单数',
            position: 'right'
          }
        ],
        series: [
          {
            name: '销售额',
            type: 'line',
            data: sales,
            smooth: true
          },
          {
            name: '订单数',
            type: 'bar',
            yAxisIndex: 1,
            data: orders
          }
        ]
      }

      chart.value.setOption(option)
    }

    // 获取销售数据
    const fetchSalesData = async () => {
      try {
        const response = await getSalesData({ days: timeRange.value })
        if (response.code === 200) {
          const { today, history, topProducts: products } = response.data
          
          Object.assign(todayData, today)
          historyData.value = history
          topProducts.value = products
          
          updateChart()
        }
      } catch (error) {
        console.error('获取销售数据失败:', error)
      }
    }

    // 获取 AI 运营洞察
    const fetchSellerInsights = async () => {
      insightLoading.value = true
      insightError.value = ''
      try {
        const response = await getSellerInsights({ days: timeRange.value })
        if (response.code === 200 && response.data) {
          insightBriefing.value = response.data.briefing || ''
          insightCards.value = response.data.cards || []
          Object.assign(insightMeta, response.data.meta || {})
        } else {
          insightError.value = response.message || 'AI 运营洞察暂不可用'
        }
      } catch (error) {
        console.error('获取 AI 运营洞察失败:', error)
        insightError.value = 'AI 运营洞察暂不可用，原有销售数据仍可继续查看。'
      } finally {
        insightLoading.value = false
      }
    }

    // 处理时间范围变化
    const handleTimeRangeChange = () => {
      fetchSalesData()
      fetchSellerInsights()
    }

    onMounted(() => {
      initChart()
      fetchSalesData()
      fetchSellerInsights()
      
      // 监听窗口大小变化，重绘图表
      window.addEventListener('resize', () => {
        chart.value?.resize()
      })
    })

    return {
      timeRange,
      todayData,
      topProducts,
      salesChart,
      insightLoading,
      insightError,
      insightBriefing,
      insightCards,
      insightMeta,
      sourceTagType,
      priorityTagType,
      priorityText,
      handleTimeRangeChange
    }
  }
}
</script>

<style scoped>
.sales-data-container {
  padding: 20px;
}

.insight-card {
  margin-bottom: 20px;
}

.insight-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
}

.insight-meta {
  color: #909399;
  font-size: 13px;
}

.insight-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.briefing-box {
  line-height: 1.7;
  color: #303133;
  background: #f5f7fa;
  border-left: 4px solid #409EFF;
  padding: 14px 16px;
  border-radius: 4px;
}

.action-card-row {
  row-gap: 16px;
}

.action-card {
  height: 100%;
  border: 1px solid #ebeef5;
}

.action-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  font-weight: 600;
}

.recommendation {
  margin: 12px 0 8px;
  color: #303133;
  line-height: 1.6;
}

.reason {
  color: #606266;
  line-height: 1.6;
  margin: 0 0 12px;
}

.evidence-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.evidence-tag {
  margin: 0;
}

.today-stats {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-content {
  text-align: center;
  padding: 20px 0;
}

.amount {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
}

.chart-card {
  margin-bottom: 20px;
}

.chart-container {
  padding: 20px 0;
}

.top-products {
  margin-bottom: 20px;
}
</style> 