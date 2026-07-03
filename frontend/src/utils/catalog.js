const CATEGORY_ICONS = [
  'el-icon-goods',
  'el-icon-mobile-phone',
  'el-icon-shopping-bag-1',
  'el-icon-refrigerator',
]

export const normalizeCategories = (categories = []) => {
  return categories.map((category, index) => ({
    id: category.categoryId || category.catid || category.id,
    name: category.categoryName || category.name || '',
    icon: category.icon || CATEGORY_ICONS[index % CATEGORY_ICONS.length],
    children: Array.isArray(category.children) ? category.children : [],
  })).filter((category) => category.id && category.name)
}

export const normalizeProducts = (products = []) => {
  return products.map((product) => ({
    id: product.productId || product.proid || product.id,
    name: product.productName || product.name || '',
    description: product.description || '',
    price: Number(product.price || 0),
    image: product.imageUrl || product.image || '',
    monthSales: product.monthSales || 0,
    shopName: product.shopName || product.sellerId || '',
    location: product.location || '',
    categoryId: product.categoryId || product.category_id || product.catid || '',
    categoryName: product.categoryName || product.category || '',
  })).filter((product) => product.id && product.name)
}
