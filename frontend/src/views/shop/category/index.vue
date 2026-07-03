<template>
  <div class="category">
    <!-- 面包屑导航 -->
    <div class="breadcrumb">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item>{{ currentCategory?.name || '全部分类' }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 分类导航 -->
    <div class="category-nav">
      <div class="category-list">
        <div v-for="category in categories" :key="category.id" class="category-item"
          :class="{ active: currentCategory?.id === category.id }" @click="handleCategoryClick(category)">
          <i :class="category.icon"></i>
          <span>{{ category.name }}</span>
        </div>
      </div>
      <div class="sub-categories" v-if="currentCategory">
        <div v-for="sub in currentCategory.children" :key="sub.id" class="sub-category">
          <h3>{{ sub.name }}</h3>
          <div class="sub-category-list">
            <div v-for="item in sub.children" :key="item.id" class="sub-category-item"
              :class="{ active: selectedCategory?.id === item.id }" @click="handleSubCategoryClick(item)">
              {{ item.name }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 筛选条件 -->
    <div class="filter-section">
      <!-- 品牌筛选 -->
      <div class="filter-item">
        <div class="filter-label">品牌：</div>
        <div class="filter-content">
          <div v-for="brand in brands" :key="brand.id" class="filter-option"
            :class="{ active: selectedBrand?.id === brand.id }" @click="handleBrandClick(brand)">
            {{ brand.name }}
          </div>
        </div>
      </div>

      <!-- 价格区间 -->
      <div class="filter-item">
        <div class="filter-label">价格：</div>
        <div class="filter-content">
          <div v-for="(range, index) in priceRanges" :key="index" class="filter-option"
            :class="{ active: selectedPriceRange === index }" @click="handlePriceRangeClick(index)">
            {{ range.label }}
          </div>
          <div class="price-input">
            <el-input-number v-model="customPriceRange.min" :min="0" :max="customPriceRange.max" placeholder="最低价" />
            <span class="separator">-</span>
            <el-input-number v-model="customPriceRange.max" :min="customPriceRange.min" placeholder="最高价" />
            <el-button @click="handleCustomPriceRange">确定</el-button>
          </div>
        </div>
      </div>

      <!-- 其他筛选条件 -->
      <div class="filter-item">
        <div class="filter-label">发货地：</div>
        <div class="filter-content">
          <div v-for="location in locations" :key="location.id" class="filter-option"
            :class="{ active: selectedLocation?.id === location.id }" @click="handleLocationClick(location)">
            {{ location.name }}
          </div>
        </div>
      </div>
    </div>

    <!-- 排序工具栏 -->
    <div class="toolbar">
      <div class="sort-buttons">
        <el-button :type="sortType === 'default' ? 'primary' : ''" @click="handleSort('default')">
          默认
        </el-button>
        <el-button :type="sortType === 'sales' ? 'primary' : ''" @click="handleSort('sales')">
          销量
        </el-button>
        <el-button :type="sortType === 'price' ? 'primary' : ''" @click="handleSort('price')">
          价格
          <el-icon v-if="sortType === 'price'">
            <component :is="sortOrder === 'asc' ? 'ArrowUp' : 'ArrowDown'" />
          </el-icon>
        </el-button>
      </div>
      <div class="view-switch">
        <el-switch v-model="isGridView" :active-icon="Grid" :inactive-icon="List" @change="handleViewChange" />
      </div>
    </div>

    <!-- 商品列表 -->
    <div class="product-list" :class="{ 'grid-view': isGridView, 'list-view': !isGridView }">
      <div v-for="product in products" :key="product.id" class="product-card" @click="handleProductClick(product)">
        <div class="product-image">
          <img :src="product.image" :alt="product.name">
        </div>
        <div class="product-info">
          <h3>{{ product.name }}</h3>
          <p class="desc">{{ product.description }}</p>
          <div class="price">¥{{ product.price.toFixed(2) }}</div>
          <div class="sales">月销 {{ product.monthSales }}+</div>
          <div class="shop-info">
            <span>{{ product.shopName }}</span>
            <span>{{ product.location }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[20, 40, 60, 80]"
        :total="total" layout="total, sizes, prev, pager, next, jumper" @size-change="handleSizeChange"
        @current-change="handleCurrentChange" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUp, ArrowDown, Grid, List } from '@element-plus/icons-vue'
import { getCategories, getProductList } from '@/api/product'
import { normalizeCategories, normalizeProducts } from '@/utils/catalog'

const route = useRoute()
const router = useRouter()

// 分类相关
const categories = ref([])
const currentCategory = ref(null)
const selectedCategory = ref(null)

const applyCategoryFromQuery = () => {
  const categoryId = String(route.query.id || route.query.categoryId || '')
  if (!categoryId) {
    return
  }

  for (const category of categories.value) {
    if (String(category.id) === categoryId) {
      currentCategory.value = category
      selectedCategory.value = null
      return
    }

    const subCategory = category.children?.find(c => String(c.id) === categoryId)
    if (subCategory) {
      currentCategory.value = category
      selectedCategory.value = subCategory
      return
    }

    for (const sub of category.children || []) {
      const item = sub.children?.find(c => String(c.id) === categoryId)
      if (item) {
        currentCategory.value = category
        selectedCategory.value = item
        return
      }
    }
  }
}

const fetchCategories = async () => {
  try {
    const res = await getCategories()
    categories.value = normalizeCategories(res.data?.categories || res.data || [])
    applyCategoryFromQuery()
    await fetchProducts()
  } catch (error) {
    console.error('获取分类失败:', error)
  }
}

const handleCategoryClick = (category) => {
  currentCategory.value = category
  selectedCategory.value = null
  updateQuery()
}

const handleSubCategoryClick = (category) => {
  selectedCategory.value = category
  updateQuery()
}

// 品牌筛选
const brands = ref([])
const selectedBrand = ref(null)

const handleBrandClick = (brand) => {
  selectedBrand.value = selectedBrand.value?.id === brand.id ? null : brand
  updateQuery()
}

// 价格区间
const priceRanges = [
  { label: '全部', min: null, max: null },
  { label: '0-100', min: 0, max: 100 },
  { label: '100-500', min: 100, max: 500 },
  { label: '500-1000', min: 500, max: 1000 },
  { label: '1000-5000', min: 1000, max: 5000 },
  { label: '5000以上', min: 5000, max: null }
]

const selectedPriceRange = ref(0)
const customPriceRange = reactive({
  min: null,
  max: null
})

const handlePriceRangeClick = (index) => {
  selectedPriceRange.value = index
  customPriceRange.min = null
  customPriceRange.max = null
  updateQuery()
}

const handleCustomPriceRange = () => {
  if (customPriceRange.min != null || customPriceRange.max != null) {
    selectedPriceRange.value = -1
    updateQuery()
  }
}

// 发货地筛选
const locations = ref([])
const selectedLocation = ref(null)

const handleLocationClick = (location) => {
  selectedLocation.value = selectedLocation.value?.id === location.id ? null : location
  updateQuery()
}

// 排序相关
const sortType = ref('default')
const sortOrder = ref('desc')

const handleSort = (type) => {
  if (type === sortType.value && type === 'price') {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortType.value = type
    sortOrder.value = 'desc'
  }
  updateQuery()
}

// 视图切换
const isGridView = ref(true)

const handleViewChange = (value) => {
  isGridView.value = value
}

// 商品列表
const products = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const fetchProducts = async () => {
  try {
    const res = await getProductList()
    const selected = selectedCategory.value || currentCategory.value
    const categoryId = selected?.id
    const categoryName = selected?.name
    let list = normalizeProducts(res.data?.list || [])

    if (categoryId || categoryName) {
      list = list.filter((product) => (
        product.categoryId === categoryId ||
        product.categoryName === categoryName
      ))
    }

    products.value = list
    total.value = list.length
  } catch (error) {
    console.error('获取商品列表失败:', error)
  }
}

const handleSizeChange = (val) => {
  pageSize.value = val
  page.value = 1
  updateQuery()
}

const handleCurrentChange = (val) => {
  page.value = val
  updateQuery()
}

// 更新查询参数
const updateQuery = () => {
  const query = {
    ...route.query,
    categoryId: selectedCategory.value?.id || currentCategory.value?.id,
    brandId: selectedBrand.value?.id,
    minPrice: customPriceRange.min || priceRanges[selectedPriceRange.value]?.min,
    maxPrice: customPriceRange.max || priceRanges[selectedPriceRange.value]?.max,
    locationId: selectedLocation.value?.id,
    sortType: sortType.value,
    sortOrder: sortOrder.value,
    page: page.value,
    pageSize: pageSize.value
  }

  // 移除空值
  Object.keys(query).forEach(key => {
    if (query[key] == null) {
      delete query[key]
    }
  })

  router.push({ query })
}

// 商品点击
const handleProductClick = (product) => {
  router.push(`/product/${product.id}`)
}

// 监听路由变化
watch(
  () => route.query,
  () => {
    fetchProducts()
  }
)

// 初始化
onMounted(() => {
  fetchCategories()
})
</script>

<style lang="scss" scoped>
@mixin text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.category {
  .breadcrumb {
    margin-bottom: 20px;
  }

  .category-nav {
    background-color: #fff;
    border-radius: 4px;
    margin-bottom: 20px;

    .category-list {
      display: flex;
      flex-wrap: wrap;
      padding: 16px;
      gap: 16px;

      .category-item {
        padding: 8px 16px;
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;

        &:hover {
          color: #409eff;
        }

        &.active {
          background-color: #409eff;
          color: #fff;
        }

        i {
          font-size: 16px;
        }
      }
    }

    .sub-categories {
      padding: 0 16px 16px;
      border-top: 1px solid #ebeef5;

      .sub-category {
        margin-top: 16px;

        h3 {
          font-size: 14px;
          margin: 0 0 12px;
        }

        .sub-category-list {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;

          .sub-category-item {
            padding: 4px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            border: 1px solid #ebeef5;

            &:hover {
              color: #409eff;
              border-color: #409eff;
            }

            &.active {
              background-color: #409eff;
              color: #fff;
              border-color: #409eff;
            }
          }
        }
      }
    }
  }

  .filter-section {
    background-color: #fff;
    border-radius: 4px;
    margin-bottom: 20px;

    .filter-item {
      display: flex;
      padding: 16px;
      border-bottom: 1px solid #ebeef5;

      &:last-child {
        border-bottom: none;
      }

      .filter-label {
        width: 80px;
        color: #909399;
      }

      .filter-content {
        flex: 1;
        display: flex;
        flex-wrap: wrap;
        gap: 12px;

        .filter-option {
          padding: 4px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 13px;

          &:hover {
            color: #409eff;
          }

          &.active {
            background-color: #409eff;
            color: #fff;
          }
        }

        .price-input {
          display: flex;
          align-items: center;
          gap: 8px;

          .separator {
            color: #909399;
          }

          .el-input-number {
            width: 120px;
          }
        }
      }
    }
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: #fff;
    border-radius: 4px;
    padding: 12px 16px;
    margin-bottom: 20px;

    .sort-buttons {
      display: flex;
      gap: 12px;
    }
  }

  .product-list {
    margin-bottom: 20px;

    &.grid-view {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 20px;

      .product-card {
        background-color: #fff;
        border-radius: 8px;
        overflow: hidden;
        cursor: pointer;
        transition: transform 0.3s, box-shadow 0.3s;

        &:hover {
          transform: translateY(-4px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .product-image {
          position: relative;
          padding-top: 100%;

          img {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
          }
        }

        .product-info {
          padding: 12px;

          h3 {
            margin: 0 0 8px;
            font-size: 14px;
            @include text-ellipsis;
          }

          .desc {
            margin: 0 0 8px;
            font-size: 12px;
            color: #999;
            @include text-ellipsis;
          }

          .price {
            color: #f56c6c;
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 4px;
          }

          .sales {
            font-size: 12px;
            color: #999;
            margin-bottom: 4px;
          }

          .shop-info {
            font-size: 12px;
            color: #666;
            display: flex;
            justify-content: space-between;
          }
        }
      }
    }

    &.list-view {
      display: flex;
      flex-direction: column;
      gap: 20px;

      .product-card {
        display: flex;
        background-color: #fff;
        border-radius: 8px;
        overflow: hidden;
        cursor: pointer;
        transition: transform 0.3s, box-shadow 0.3s;

        &:hover {
          transform: translateY(-4px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .product-image {
          width: 200px;
          height: 200px;
          flex-shrink: 0;

          img {
            width: 100%;
            height: 100%;
            object-fit: cover;
          }
        }

        .product-info {
          flex: 1;
          padding: 20px;
          display: flex;
          flex-direction: column;

          h3 {
            margin: 0 0 12px;
            font-size: 16px;
          }

          .desc {
            margin: 0 0 16px;
            font-size: 14px;
            color: #666;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
          }

          .price {
            color: #f56c6c;
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 8px;
          }

          .sales {
            font-size: 14px;
            color: #999;
            margin-bottom: 8px;
          }

          .shop-info {
            margin-top: auto;
            font-size: 14px;
            color: #666;
            display: flex;
            justify-content: space-between;
          }
        }
      }
    }
  }

  .pagination {
    display: flex;
    justify-content: flex-end;
  }
}

@mixin text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
