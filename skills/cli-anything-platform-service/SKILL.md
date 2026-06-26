---
name: "睿锋平台CLI"
description: "睿峰智链汽车配件供应链平台 CLI 管理工具。通过命令行与 platform-service REST API 交互，覆盖产品、客户/供应商、用户、库存、购物车、报价、采购单、出入库、价格清单/价格变更审批、对账单等后台业务模块的查询与 CRUD 管理。触发条件：后台产品库搜索/产品详情、价格清单与价格变更审批、报价/采购单/出入库管理、客户/供应商/用户/角色/菜单管理等平台后台运营操作。"
---

# cli-anything-platform-service

睿峰智链汽车配件供应链平台 CLI 管理工具。

## Installation

仓库根目录执行：

```bash
pip install -e .
```

Requires: Python >= 3.10, click, prompt_toolkit, requests.

## Quick Start

```bash
# Login (recommended): saves token AND credentials; expired tokens auto-relogin on 401
cli-anything-platform-service config login --mobile YOUR_MOBILE

# Or configure manually
cli-anything-platform-service config set --base-url https://api.example.com --token YOUR_TOKEN

# Test connection
cli-anything-platform-service config test

# List products (JSON output for agent consumption)
cli-anything-platform-service --json product list --page 1 --size 10

# Enter interactive REPL mode
cli-anything-platform-service
```

Environment variables: `PLATFORM_BASE_URL`, `PLATFORM_TOKEN`, `PLATFORM_MOBILE`, `PLATFORM_PASSWORD`.

**Auto re-login**: after `config login`, credentials are saved per-env in config.json (chmod 600). Token 过期会自动重新登录并重试——覆盖两种过期形式：传输层 `HTTP 401`，以及网关常见的业务信封层 `HTTP 200 + body {"code":401}`。无需手动刷新 token。

## Command Groups

| Command | API Base | Description |
|---------|----------|-------------|
| `config` | - | 连接配置管理 |
| `product` | `/api/product` | 产品管理 (CRUD, 上下架, 导入导出, ES同步) |
| `company` | `/api/company` | 客户/供应商管理 (CRUD, 审核, 锁定/解锁, 认证) |
| `user` | `/api/user` | 用户管理 (CRUD, 企微绑定) |
| `inventory` | `/api/inventory` | 库存管理 (搜索, ES同步) |
| `shopping-cart` | `/api/shoppingCart` | 购物车管理 (CRUD, 批量删除) |
| `price` | `/api/price` | 价格解析管理 (C0DIG0解析, 报价导出) |
| `price-approval` | `/api/priceChangeApproval` | 价格变更审批 (列表/通过/拒绝/批量审批/导入) |
| `price-list` | `/api/priceList` | 价格清单管理 (CRUD, 全部查询) |
| `price-item` | `/api/priceListItem` | 价格清单明细管理 (CRUD, 导入) |
| `quotation` | `/api/quotation` | 报价管理 (CRUD) |
| `purchase-order` | `/api/purchaseOrder` | 采购单管理 (供应商/客户采购单CRUD) |
| `stock-order` | `/api/stockOrder` | 出入库管理 (入库/出库, 库位设置, 过账) |
| `menu` | `/api/menu` | 菜单管理 |
| `role` | `/api/role` | 角色管理 (CRUD) |
| `warehouse` | `/api/warehouse` | 仓库管理 (CRUD) |
| `product-category` | `/api/productCategory` | 产品分类管理 (树形结构, 批量更新) |
| `payment-term` | `/api/paymentTerm` | 付款条件管理 (CRUD) |
| `statement` | `/api/statement` | 对账单管理 (查询, 导出) |

## Price Approval 命令组 (价格变更审批)

### 命令列表

| Command | 说明 |
|---------|------|
| `price-approval pending [--status] [--batch-no]` | 审批列表（按状态/批次筛选） |
| `price-approval find-by-id --id <ID>` | 审批记录详情 |
| `price-approval approve --id <ID> [--remark]` | 审批通过 |
| `price-approval reject --id <ID> [--remark]` | 审批拒绝 |
| `price-approval batch-summary` | 批次审批汇总 |
| `price-approval approve-batch --batch-no <号>` | 按批次整体通过 |
| `price-approval reject-batch --batch-no <号>` | 按批次整体拒绝 |
| `price-approval approve-by-ids --ids-json <JSON>` | 批量通过（勾选多条） |
| `price-approval reject-by-ids --ids-json <JSON>` | 批量拒绝（勾选多条） |
| `price-approval import --file <Excel> --price-type <编码>` | Excel导入价格变更（2-P2/3-P3/6-采购价/10-OEM价） |
| `price-approval import-multi-price --file <Excel>` | 批量导入多种价格变更 |

### 使用示例

```bash
# 查看待审批列表
cli-anything-platform-service price-approval pending --status 0

# 按产品编码搜索待审批记录
cli-anything-platform-service price-approval pending --code 39720037

# 查看批次汇总
cli-anything-platform-service price-approval batch-summary

# 审批通过单条
cli-anything-platform-service price-approval approve --id ABC123 --remark "价格合理"

# 按批次整体通过
cli-anything-platform-service price-approval approve-batch --batch-no BATCH20260601

# 批量通过多条
cli-anything-platform-service price-approval approve-by-ids --ids-json '["id1","id2"]'

# 导入价格变更Excel
cli-anything-platform-service price-approval import --file 价格变更.xlsx --price-type 6

# 导入多种价格变更
cli-anything-platform-service price-approval import-multi-price --file 多种价格修改.xlsx
```

## Price List 命令组 (价格清单)

### 命令列表

| Command | 说明 |
|---------|------|
| `price-list list [--name] [--type] [--status]` | 价格清单列表 |
| `price-list find-all` | 全部启用的价格清单（下拉选择） |
| `price-list find-by-id --id <ID>` | 价格清单详情 |
| `price-list create --name <名称> [--type] [--status]` | 新增价格清单 |
| `price-list update --id <ID> [--name] [--status]` | 更新价格清单 |
| `price-list delete --id <ID>` | 删除价格清单 |

### 使用示例

```bash
# 查看价格清单
cli-anything-platform-service price-list list

# 新建P2价格清单
cli-anything-platform-service price-list create --name "2026年P2价格表" --type P2 --status 1

# 查询全部
cli-anything-platform-service price-list find-all
```

## Price Item 命令组 (价格清单明细)

### 命令列表

| Command | 说明 |
|---------|------|
| `price-item list --price-list-id <ID> [--keyword]` | 价格清单明细列表 |
| `price-item find-by-price-list --price-list-id <ID>` | 按价格清单ID查所有明细 |
| `price-item find-by-id --id <ID>` | 明细详情 |
| `price-item create --price-list-id <ID> --product-id <ID> --price <价>` | 新增明细 |
| `price-item update --id <ID> [--price]` | 更新明细（价格修改自动提交审批） |
| `price-item delete --id <ID>` | 删除明细 |
| `price-item import --price-list-id <ID> --file <Excel>` | 导入价格清单明细 |

### 使用示例

```bash
# 查看某价格清单的明细
cli-anything-platform-service price-item list --price-list-id PL001

# 按关键字搜索明细
cli-anything-platform-service price-item list --price-list-id PL001 --keyword 轴承

# 新增明细
cli-anything-platform-service price-item create --price-list-id PL001 --product-id P001 --price 120.50

# 导入明细Excel
cli-anything-platform-service price-item import --price-list-id PL001 --file 明细.xlsx
```

### 前置依赖
- 价格与后台相关命令 (`price-*` / `product` / `company` 等) 依赖 `~/.cli-anything-platform-service/config.json` 中的连接配置
- 价格清单明细 (`price-item update`) 价格修改会自动提交价格变更审批

## Agent Usage Guidance

### JSON Output Mode

All commands support `--json` flag for machine-readable output. This is the recommended mode for AI agents.

```bash
cli-anything-platform-service --json product list --page 1 --size 5
```

### Standard Response Format

The API returns a unified `Message` wrapper:
```json
{
  "code": 200,
  "msg": "操作成功",
  "status": true,
  "data": { ... }
}
```

Paginated endpoints return `PageResult`:
```json
{
  "data": {
    "content": [ ... ],
    "totalElements": 100,
    "totalPages": 10,
    "page": 1,
    "size": 15
  }
}
```

### Common Patterns

**CRUD operations** follow RESTful conventions:
```bash
# List
cli-anything-platform-service --json <resource> list [filters...] --page 1 --size 15

# Get by ID
cli-anything-platform-service --json <resource> get --id <UUID>

# Create (POST with required fields)
cli-anything-platform-service --json <resource> create --<field1> <val1> --<field2> <val2> ...

# Update
cli-anything-platform-service --json <resource> update --id <UUID> --<field> <newval> ...

# Delete
cli-anything-platform-service --json <resource> delete --id <UUID>
```

**Field documentation** is available via `comment` sub-command for most resources:
```bash
cli-anything-platform-service --json product comment
```

### Error Handling

- The CLI exits with non-zero status on API errors
- Error messages are in Chinese
- Token 过期（传输层 HTTP 401 或业务信封层 `code:401`）= auto re-login kicks in if credentials were saved via `config login`; only surfaces as an error when re-login also fails
- HTTP 403 = insufficient permissions
- HTTP 404 = resource not found

### Configuration Persistence

Config is saved to `~/.cli-anything-platform-service/config.json`. Tokens are stored and can be pre-configured via `config set`.
