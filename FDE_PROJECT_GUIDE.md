# XD-GO FDE 项目说明

本文档用于说明当前 FDE 改进版 XD-GO 项目的本地启动与关闭方式、已实现功能，以及该项目如何体现 Forward Deployed Engineer 面试所需要的关键能力。

## 1. 项目定位

XD-GO 原本是一个前后端分离的线上购物系统，包含买家浏览商品、购物车、下单，以及卖家商品管理、订单管理、销售数据查看等基础电商能力。

当前版本在原有系统上增加了面向卖家的 **Sales Insight Copilot**，模拟传统电商平台在 AI 转型过程中，由 FDE 将大模型能力嵌入真实业务流程的改造方式。它不是单独做一个聊天窗口，而是在卖家已有销售数据页中，基于订单、库存、热销商品、滞销商品和履约状态生成运营简报与行动建议。

## 2. 本地启动项目

### 2.1 前置条件

本地需要准备：

- MySQL，当前本地开发库名为 `xd_go`
- Python 虚拟环境，位于 `backend/.venv`
- Node.js 和 npm
- 项目根目录下的 `.env` 文件

`.env` 用于存放本地 secret，不要提交到 Git。示例字段如下：

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://openrouter.fans/v1
DEEPSEEK_TIMEOUT_SECONDS=20
```

注意：真实 API key 只放在本地 `.env` 或部署平台环境变量中，不要写入 README、代码或提交历史。

### 2.2 启动 MySQL

检查 MySQL 是否运行：

```bash
brew services list
lsof -nP -iTCP:3306 -sTCP:LISTEN
```

如果没有运行：

```bash
brew services start mysql
```

如果服务异常，可重启：

```bash
brew services restart mysql
```

### 2.3 初始化或重建开发数据库

如果是第一次启动，或本地 migration 状态混乱，可以重建开发库：

```bash
MYSQL_PWD=003620 mysql -u root -e "DROP DATABASE IF EXISTS xd_go; CREATE DATABASE xd_go CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

然后用当前 SQLAlchemy models 创建表并生成测试数据：

```bash
cd /Users/luoliwen/XD-GO/backend
source .venv/bin/activate
set -a
source ../.env
set +a
PYTHONPATH=.. python generate_test_data.py
```

说明：当前仓库的 Alembic migration 链存在历史冲突，本地演示建议使用 `generate_test_data.py` 的 `db.create_all()` 路径初始化数据库，而不是直接执行 `python app.py` 触发 migration upgrade。

### 2.4 启动后端

macOS 的 Control Center / AirPlay Receiver 可能占用 `5000` 端口，因此当前本地推荐后端运行在 `5001`。

```bash
cd /Users/luoliwen/XD-GO/backend
source .venv/bin/activate
set -a
source ../.env
set +a
PYTHONPATH=.. flask --app app run --host 0.0.0.0 --port 5001
```

后端启动后访问：

```text
http://127.0.0.1:5001
```

可用接口验证：

```bash
curl http://127.0.0.1:5001/api/product/productList
```

### 2.5 启动前端

```bash
cd /Users/luoliwen/XD-GO/frontend
npm install
npm run dev -- --host 0.0.0.0
```

前端启动后访问：

```text
http://localhost:5173/
```

当前本地前端请求配置位于：

```text
frontend/src/utils/request.js
```

其中：

```js
baseURL: 'http://127.0.0.1:5001'
timeout: 30000
```

### 2.6 测试账号

测试数据生成后可使用：

```text
卖家账号：jane_smith / seller123
买家账号：john_doe / buyer123
管理员账号：admin / admin123
```

登录卖家账号后，进入卖家销售数据页即可看到“AI 运营洞察”面板。

## 3. 关闭项目

如果前后端运行在当前终端中，分别按：

```text
Ctrl + C
```

如果找不到运行终端，可以按端口关闭：

```bash
lsof -ti tcp:5001 | xargs kill
lsof -ti tcp:5173 | xargs kill
```

确认端口已释放：

```bash
lsof -nP -iTCP:5001 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

没有输出即表示后端和前端已经停止。

MySQL 如需关闭：

```bash
brew services stop mysql
```

## 4. 当前项目已实现功能

### 4.1 原有电商功能

- 用户注册、登录和基础用户信息管理
- 买家浏览商品、搜索商品、查看商品详情
- 买家购物车管理
- 买家下单、支付回调、查看订单状态
- 卖家商品发布、商品列表、商品编辑
- 卖家订单管理和订单状态更新
- 卖家销售数据页，包含今日销售、订单数、销售趋势和热销商品

### 4.2 FDE 改进功能：Sales Insight Copilot

当前版本新增了面向卖家的 AI 运营洞察功能：

- 新增后端接口：

```text
GET /api/sell_order/insights?days=30
```

- 支持 7 / 30 / 90 天时间窗口
- 复用原有 seller 鉴权，只允许卖家访问
- 聚合订单、商品、库存和销售数据
- 输出中文运营简报
- 输出多张行动卡片，包括：
  - 待发货订单处理建议
  - 低库存商品补货建议
  - 滞销商品促活建议
  - 核心收入商品保护建议
- 每张行动卡包含优先级、建议、原因、证据指标和 metric 标识
- 前端销售数据页顶部新增“AI 运营洞察”面板
- 面板支持 loading、empty、error、source badge、生成时间、运营简报和行动卡片
- 切换 7 / 30 / 90 天时，原有图表和 AI 洞察同步刷新

### 4.3 大模型与 fallback

后端通过 OpenAI-compatible SDK 调用 DeepSeek/OpenRouter：

```text
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://openrouter.fans/v1
```

如果模型调用成功，接口返回：

```json
{
  "meta": {
    "source": "deepseek"
  }
}
```

如果未配置 API key、模型超时、网络失败或模型返回非合法 JSON，后端会自动使用 deterministic fallback，返回同样结构的数据：

```json
{
  "meta": {
    "source": "fallback"
  }
}
```

这样即使模型不可用，页面也能稳定展示运营洞察，不会中断卖家工作流。

### 4.4 RAG 知识库增强

当前版本进一步加入轻量 RAG 能力，将卖家实时经营指标与本地电商运营知识库结合：

- 后端新增 `backend/knowledge/seller_ops/` 运营知识库
- 覆盖库存补货、滞销处理、履约风险、收入集中度和促销组合策略
- 后端根据销售指标自动检索相关知识片段
- DeepSeek 生成运营洞察时同时参考结构化销售数据和检索知识
- 前端 AI 面板展示“知识增强”状态与参考知识来源
- 模型不可用或知识库不可用时仍保持 fallback，保证演示稳定性

这一改造体现了 FDE 在客户现场常见的交付方式：将客户业务 SOP 和平台经验沉淀为知识库，再接入真实业务数据与大模型，形成可复用的 AI 工作流。

## 5. 这个项目如何体现 FDE 能力

### 5.1 从模糊需求到可落地方案

FDE 面对的需求通常不是“实现某个按钮”，而是“我们想把 AI 加进现有业务里”。本项目将“传统电商系统 AI 化”拆解为一个清晰的卖家场景：帮助商家理解销售表现，并给出下一步运营动作。

项目没有选择泛泛的聊天机器人，而是把 AI 嵌入卖家的销售数据页，让模型输出围绕订单、库存、商品表现和履约状态展开。这体现了 FDE 对客户业务场景、用户路径和交付价值的理解。

### 5.2 在现有系统中做增量改造

真实 FDE 工作往往需要在客户已有系统中交付，而不是从零开始重写。本项目在不修改数据库 schema 的前提下，复用现有的 `Order`、`OrderItem`、`Product`、`User` 数据模型，新增 seller insight 服务层和 API。

这种方式降低了改造风险，也更符合企业 AI 转型中的渐进式落地路径。

### 5.3 全栈端到端交付

该项目覆盖了从数据到界面的完整链路：

- 后端数据聚合
- 模型调用
- fallback 兜底
- API schema 设计
- 前端状态管理
- 卖家页面集成
- 本地启动与演示流程

这体现了 FDE 需要具备的端到端交付能力：不仅能写模型调用，也能让它进入真实产品路径，并最终被业务用户使用。

### 5.4 AI 可靠性与演示稳定性

面试或客户现场 demo 中，模型服务可能因为网络、额度、超时、格式错误等原因失败。本项目设计了 deterministic fallback，使接口始终返回统一 schema。

这体现了 FDE 对“现场可用性”的重视：AI 能力可以增强体验，但不能成为系统单点故障。

### 5.5 安全与配置意识

项目中 API key 只通过环境变量读取，不写入代码、README 或提交历史。本地 `.env` 被 `.gitignore` 忽略，远端只保留 `.env.example`。

这体现了 FDE 在客户环境中处理 secret、配置和部署差异时需要具备的基本安全意识。

### 5.6 面向业务结果表达技术价值

Sales Insight Copilot 输出的不是模型炫技，而是业务动作：

- 哪些订单需要优先处理
- 哪些商品可能缺货
- 哪些商品库存高但卖不动
- 店铺收入是否过度依赖少数商品

这种表达方式能把工程实现转化为业务语言，帮助面试官看到你不只是“会接 API”，而是能把 AI 能力落到客户业务结果上。

## 6. 面试讲述建议

可以用下面这段作为项目讲述开场：

> 这个项目原本是一个已可运行的电商系统。我把它改造成一个 FDE 面试作品，模拟传统电商平台在 AI 转型时，如何把大模型能力嵌入卖家运营工作流。我没有做孤立聊天窗口，而是在卖家销售数据页中新增 Sales Insight Copilot，基于订单、销售额、库存、热销和滞销商品生成中文简报与行动卡。后端接入 DeepSeek/OpenRouter，同时设计 fallback，确保无 key、超时或模型输出异常时系统仍然稳定可演示。

面试中可以重点强调：

- 我如何把“AI 化改造”拆解为具体业务场景
- 我如何在已有系统里做低风险增量改造
- 我如何落地 RAG 场景：不是单独做聊天机器人，而是在卖家经营分析流程中检索运营 SOP，并生成带业务依据的行动建议
- 我如何设计模型输出 schema 和 fallback
- 我如何保证 demo 稳定、secret 安全和用户体验连续
- 我如何完成前后端端到端交付

## 7. 常见问题

### 为什么后端用 5001？

macOS 的 Control Center / AirPlay Receiver 常会占用 `5000`。为了避免冲突，本地后端运行在 `5001`，前端请求地址也指向 `http://127.0.0.1:5001`。

### 为什么不用 `python app.py`？

当前仓库历史 migration 链存在冲突，`python app.py` 会触发 `flask_migrate.upgrade()`，可能出现 migration revision 或重复建表错误。本地演示建议用：

```bash
PYTHONPATH=.. flask --app app run --host 0.0.0.0 --port 5001
```

数据库表通过：

```bash
PYTHONPATH=.. python generate_test_data.py
```

创建。

### 为什么有时显示 Fallback？

Fallback 表示模型调用没有成功返回合法 JSON，可能原因包括：

- API key 未配置
- 模型服务超时
- 网络不可用
- 模型返回非 JSON 文本
- cards 为空或字段不符合预期

Fallback 是有意设计的稳定兜底，不代表页面或后端功能失败。
