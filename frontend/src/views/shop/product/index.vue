<template>
  <div class="product-container">
    <div class="product-content">
      <!-- 商品基本信息 -->
      <div class="product-basic">
        <!-- 商品图片 -->
        <div class="product-gallery">
          <el-carousel trigger="click" height="400px" :autoplay="false">
              <el-image :src="curGood.imageUrl" fit="contain" />
          </el-carousel>
        </div>

        <!-- 商品信息 -->
        <div class="product-info">
          <h1 class="product-name">{{ curGood.productName }}</h1>
          <div class="product-brief">{{ curGood.brief }}</div>

          <div class="product-price">
            <div class="current-price">
              <span class="label">价格</span>
              <span class="price">¥{{ curGood.price }}</span>
            </div>
          </div>

          <div class="product-sales">
            <span class="label">库存</span>
            <span class="value">{{ curGood.stock }}件</span>
          </div>

          <!-- 数量选择 -->
          <div class="product-quantity">
            <span class="label">数量</span>
            <el-input-number v-model="quantity" :min="1" :max="curGood.stock" :step="1" />
            <span class="stock">库存：{{ curGood.stock }}件</span>
          </div>

          <!-- 操作按钮 -->
          <div class="product-actions">
            <el-button type="primary" size="large" @click="handleAddToCart" :loading="loading">
              加入购物车
            </el-button>
            <el-button type="danger" size="large" @click="handleBuyNow" :loading="loading">
              立即购买
            </el-button>
          </div>
        </div>
      </div>

      <!-- 商品详情 -->
      <!-- <div class="product-detail">
        <el-tabs>
          <el-tab-pane label="商品详情">
            <div class="detail-content" v-html="curGood.description"></div>
          </el-tab-pane>
          <el-tab-pane label="商品评价">
            <div class="comments-list">
              <div v-for="comment in product.comments" :key="comment.id" class="comment-item">
                <div class="comment-user">
                  <el-avatar :src="comment.avatar" />
                  <span class="username">{{ comment.user }}</span>
                </div>
                <div class="comment-content">
                  <el-rate v-model="comment.rating" disabled />
                  <p class="text">{{ comment.content }}</p>
                  <div class="time">{{ comment.time }}</div>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div> -->
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { ElMessage } from 'element-plus'
import { useGoodsStore } from '@/stores/goods'
import { addToCart } from '@/api/shop'

const router = useRouter()
const route = useRoute()
const cartStore = useCartStore()
const goodsStore = useGoodsStore()

const curGood = ref(null)
curGood.value = goodsStore.curGood(route.params.id).value
console.log(curGood.value);

// 购买数量
const quantity = ref(1)
const loading = ref(false)

// 加入购物车
const handleAddToCart = async () => {
  try {
    loading.value = true
    await addToCart({
      proid: curGood.value.productId,
      quantity: quantity.value
    })
    await cartStore.loadCart()
    ElMessage.success('已添加到购物车')
    return true
  } catch (error) {
    console.error('加入购物车失败:', error)
    ElMessage.error('加入购物车失败，请确认已登录后重试')
    return false
  } finally {
    loading.value = false
  }
}

// 立即购买
const handleBuyNow = async () => {
  const added = await handleAddToCart()
  if (added) {
    router.push('/cart')
  }
}
</script>

<style lang="scss" scoped>
.product-container {
  max-width: 1200px;
  margin: 20px auto;
  padding: 0 20px;

  .product-content {
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  }

  .product-basic {
    display: grid;
    grid-template-columns: 500px 1fr;
    gap: 40px;
    padding: 20px;
  }

  .product-gallery {
    .el-image {
      width: 100%;
      height: 100%;
    }
  }

  .product-info {
    .product-name {
      font-size: 24px;
      font-weight: bold;
      margin: 0 0 10px;
    }

    .product-brief {
      color: #666;
      margin-bottom: 20px;
    }

    .product-price {
      margin-bottom: 20px;
      padding: 20px;
      background-color: #f5f7fa;
      border-radius: 4px;

      .current-price {
        display: flex;
        align-items: baseline;
        gap: 10px;
        margin-bottom: 10px;

        .label {
          font-size: 14px;
          color: #666;
        }

        .price {
          font-size: 28px;
          color: #f56c6c;
          font-weight: bold;
        }
      }

      .original-price {
        color: #999;
        text-decoration: line-through;
      }
    }

    .product-sales {
      margin-bottom: 20px;

      .label {
        color: #666;
        margin-right: 10px;
      }

      .value {
        color: #333;
      }
    }

    .product-specs {
      margin-bottom: 20px;

      .spec-item {
        margin-bottom: 15px;

        .spec-name {
          margin-bottom: 10px;
          color: #666;
        }

        .spec-values {
          .el-radio-button {
            margin-right: 10px;
            margin-bottom: 10px;
          }
        }
      }
    }

    .product-quantity {
      display: flex;
      align-items: center;
      gap: 15px;
      margin-bottom: 30px;

      .label {
        color: #666;
      }

      .stock {
        color: #999;
        font-size: 14px;
      }
    }

    .product-actions {
      display: flex;
      gap: 20px;
    }
  }

  .product-detail {
    padding: 20px;

    .detail-content {
      padding: 20px 0;

      img {
        max-width: 100%;
        height: auto;
        margin: 10px 0;
      }
    }
  }

  .comments-list {
    .comment-item {
      padding: 20px 0;
      border-bottom: 1px solid #ebeef5;

      &:last-child {
        border-bottom: none;
      }

      .comment-user {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;

        .username {
          color: #333;
        }
      }

      .comment-content {
        .text {
          margin: 10px 0;
          color: #666;
        }

        .time {
          color: #999;
          font-size: 14px;
        }
      }
    }
  }
}
</style>
