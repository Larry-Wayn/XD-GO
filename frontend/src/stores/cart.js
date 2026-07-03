import { defineStore } from 'pinia'
import { getCartList } from '@/api/shop'

const normalizeCartProduct = (product, selected = true) => {
  const id = product.proid || product.productId || product.id

  return {
    id,
    proid: id,
    name: product.name || product.productName || '',
    price: Number(product.price || 0),
    image: product.image || product.imageUrl || '',
    quantity: Number(product.quantity || 1),
    selected,
    specs: product.specs || null,
  }
}

export const useCartStore = defineStore('cart', {
  state: () => ({
    items: [],
    loading: false,
    loaded: false,
  }),

  getters: {
    // 商品总数
    count: (state) => state.items.reduce((sum, item) => sum + item.quantity, 0),

    // 购物车页使用的商品总数别名
    totalCount: (state) => state.items.reduce((sum, item) => sum + item.quantity, 0),

    // 已选商品数量
    selectedCount: (state) => state.items.filter((item) => item.selected).length,

    // 已选商品总价
    totalPrice: (state) =>
      state.items
        .filter((item) => item.selected)
        .reduce((sum, item) => sum + item.price * item.quantity, 0),

    // 是否全选
    isAllSelected: (state) => state.items.length > 0 && state.items.every((item) => item.selected),
  },

  actions: {
    // 使用后端购物车作为唯一数据源，避免 mock id 被提交到真实下单接口。
    setItems(products = []) {
      const selectedById = new Map(this.items.map((item) => [item.id, item.selected]))
      this.items = products.map((product) => {
        const id = product.proid || product.productId || product.id
        return normalizeCartProduct(product, selectedById.get(id) ?? true)
      })
      this.loaded = true
    },

    async loadCart() {
      this.loading = true
      try {
        const res = await getCartList()
        this.setItems(res?.data?.products || [])
        return this.items
      } finally {
        this.loading = false
      }
    },

    // 添加商品到购物车
    addToCart(product, quantity = 1) {
      const normalized = normalizeCartProduct(product)
      const existItem = this.items.find((item) => item.id === normalized.id)
      if (existItem) {
        existItem.quantity += quantity
      } else {
        this.items.push({
          ...normalized,
          quantity,
          selected: true,
        })
      }
      this.loaded = true
    },

    // 从购物车移除商品
    removeFromCart(productId) {
      const index = this.items.findIndex((item) => item.id === productId)
      if (index > -1) {
        this.items.splice(index, 1)
      }
    },

    // 更新商品数量
    updateQuantity(productId, quantity) {
      const item = this.items.find((item) => item.id === productId)
      if (item) {
        item.quantity = quantity
      }
    },

    // 切换商品选中状态
    toggleSelected(productId) {
      const item = this.items.find((item) => item.id === productId)
      if (item) {
        item.selected = !item.selected
      }
    },

    // 切换全选状态
    toggleSelectAll() {
      const targetValue = !this.isAllSelected
      this.items.forEach((item) => {
        item.selected = targetValue
      })
    },

    // 清空购物车
    clearCart() {
      this.items = []
      this.loaded = true
    },
  },
})
