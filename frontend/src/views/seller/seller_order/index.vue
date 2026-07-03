<template>
    <div>
        <template v-if="loading">
            <p>Pageloading,waiting...</p>
        </template>
        <template v-else>
            <el-table :data="OrderList"
                stripe
                style="width: 100%">
                <el-table-column prop="orderid"
                    label="OrderId"
                    width="180" />
                <el-table-column prop="buyer_info.name"
                    label="BuyerName"
                    width="180" />
                <el-table-column prop="buyer_info.phone"
                    label="BuyerPhone"
                    width="180" />
                <el-table-column prop="buyer_info.address"
                    label="BuyerAdress"
                    width="200" />
                <el-table-column prop="totalprice"
                    label="TotalPrice"
                    width="180" />
                <el-table-column prop="status"
                    label="status"
                    width='180' />
                <el-table-column prop="createtime"
                    label="CreateTime" />
                <el-table-column fixed="right"
                    label="Options"
                    min-width="120">
                    <template #default="scope">
                        <el-button link
                            type="primary"
                            size="small"
                            :disabled="scope.row.status !== 'pending'"
                            @click.prevent="Editorder(scope.row.orderid)">
                            {{ getActionText(scope.row.status) }}
                        </el-button>
                    </template>
                </el-table-column>
            </el-table>
        </template>
    </div>
</template>
<script setup>
import { useGetOrder, useShiporder } from '@/stores/seller_products';
import { ElMessage } from 'element-plus'
import { ref, watchEffect, onMounted } from 'vue'
const loading = ref(true);//加载对象
const OrderList = ref([])
const GetOrder = useGetOrder()
const Shiporder = useShiporder()

const loadOrders = async () => {
    loading.value = true;
    try {
        await GetOrder.getorders();
        OrderList.value = GetOrder.orderList;
    } catch (error) {
        console.error('获取订单失败:', error)
        ElMessage.error('获取订单失败，请稍后重试');
    } finally {
        loading.value = false;
    }
}

//整个组件挂载后的行为
onMounted(() => {
    loadOrders();
});

const getActionText = (status) => {
    const actionMap = {
        pending: 'Deliver',
        shipped: 'Shipped',
        delivered: 'Completed',
        unpaid: 'Waiting Payment'
    }
    return actionMap[status] || 'Deliver'
}

const Editorder = async (id) => {
    try {
        await Shiporder.shipOrderstatus(id, 'shipped');
        await loadOrders();
        ElMessage.success('订单状态已更新为已发货');
    } catch (error) {
        console.error('修改订单状态失败:', error)
        ElMessage.error('修改订单状态失败，请稍后重试');
    }
}

//监听数据变化同步数据变化
watchEffect(() => {
    console.log('orderlist 发生变化:', GetOrder.orderList);
    OrderList.value = GetOrder.orderList;
    if (GetOrder.orderList.length > 0) {
        loading.value = false;//不要忘记加载
    }
});
</script>
