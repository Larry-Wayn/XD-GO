import request from '@/utils/request'

// 获取商品列表
export function getProductList(params) {
  return request({
    url: '/api/product/productList',
    method: 'get',
    params
  })
}

// 获取商品详情
export function getProductDetail(id) {
  return request({
    url: `/api/sell_order/seller_detail`,
    method: 'get',
    params: {
      goodsId: id
    }
  })
}

// 获取商品分类
export function getCategories() {
  return request({
    url: '/api/product/category',
    method: 'get'
  })
}

// 卖家 - 创建商品
export function createProduct(data) {
  return request({
    url: '/api/sell_order/addProduct',
    method: 'post',
    data
  })
}

// 卖家 - 更新商品
export function updateProduct(data) {
  return request({
    url: `/api/sell_order/updateProduct`,
    method: 'put',
    data
  })
}

// 卖家 - 删除商品
export function deleteProduct(id) {
  return request({
    url: `/api/sell_order/deleteProduct`,
    method: 'delete',
    data: {
      proid: id
    }
  })
}
