# SCAME-CLI Harness: 产品数据 → Agent 可调用的 CLI

## Purpose

本 Harness 定义了一套标准流程（SOP），用于将 SCAME 工业连接器的产品数据（面价表、库存、产品知识库、历史报价）封装为 AI Agent 可直接调用的 CLI 工具。

目标：让 Claude Code / 企业微信机器人 / 飞书机器人 / 钉钉机器人 可以用命令行查询产品、选型、报价，无需人工翻 Excel。

---

## General SOP: 将产品数据变成 Agent-Usable CLI

### Phase 1: 数据源分析

1. **识别数据源** — 当前 SCAME 项目有以下可结构化数据：

   | 数据源 | 格式 | 位置 | 用途 |
   |--------|------|------|------|
   | 面价表（含选型型号） | CSV | `04_报价库存面价_本地业务数据/当前开发业务数据/2026_SCAME_面价表_包含选型型号.csv` | 产品查询、选型、报价基础 |
   | 面价表（不含选型型号） | CSV | `04_报价库存面价_本地业务数据/当前开发业务数据/2026_SCAME_面价表_不包含选型型号.csv` | 标准品报价 |
   | 库存数据 | XLSX | `04_报价库存面价_本地业务数据/当前开发业务数据/模板-销售现存量查询*.xlsx` | 实时库存查询 |
   | 历史报价 | CSV | `04_报价库存面价_本地业务数据/历史报价记录/` | 参考报价、价格趋势 |
   | 产品知识库 | MD/DOCX | `02_产品资料库/scame产品知识库/` | 技术参数、应用场景 |
   | 报价模板 | XLSX | `04_报价库存面价_本地业务数据/报价模板/` | 生成报价单 |

2. **分析面价表字段**（核心数据模型）：

   ```python
   @dataclass
   class Product:
       产品型号: str        # 例: "213.1630"
       产品描述: str        # 例: "PLUG 2P+E IP44 16A 4h 100-130V AC"
       产品类型: str        # 例: "IP44 OPTIMA Plugs"
       面价_pcs: float      # 例: 78.0
       最小起订量: float    # 例: 10.0
       产品图片链接: str    # scame.com 图片 URL
       技术说明书链接: str   # scame.com 产品页
   ```

3. **识别查询模式** — 客户典型提问：

   - **正向查询**: "213.1630 多少钱？" → 按型号查价格
   - **反向查询**: "有没有 IP67 的 63A 插头？" → 按参数筛选
   - **模糊查询**: "给数据中心推荐插头" → 按应用场景推荐
   - **替代查询**: "213.1630 有没有便宜替代？" → 同类型比价
   - **库存查询**: "这个型号有货吗？" → 关联库存数据
   - **报价生成**: "客户要 50 个 213.1630，报个价" → 生成报价单

### Phase 2: CLI 架构设计

1. **交互模型**：双模 — Subcommand CLI（一次性查询）+ REPL（连续对话）

2. **命令组**：

   | 命令组 | 命令 | 说明 |
   |--------|------|------|
   | **product** | `search` | 按型号/关键词搜索产品 |
   | | `info` | 查看产品详细信息 |
   | | `filter` | 按参数筛选（电流、极数、防护等级、电压） |
   | | `compare` | 对比多个产品 |
   | **pricing** | `price` | 查询单品面价 |
   | | `quote` | 生成报价单（含折扣、数量） |
   | | `history` | 查看历史报价记录 |
   | **stock** | `check` | 查询库存 |
   | | `available` | 列出有货产品 |
   | **recommend** | `by-scenario` | 按应用场景推荐（数据中心、港口、轨交） |
   | | `alternative` | 找替代品 |
   | **catalog** | `categories` | 列出产品类型 |
   | | `export` | 导出产品列表 |
   | **session** | `status` | 当前会话状态 |
   | | `history` | 查询历史 |
   | | `undo` | 撤销 |

3. **状态模型**：

   ```python
   @dataclass
   class Session:
       selected_products: List[Product]  # 当前选中产品
       quote_items: List[QuoteItem]      # 报价单项目
       _undo_stack: List[Dict]           # 撤销栈
       _redo_stack: List[Dict]           # 重做栈
       _modified: bool                   # 脏标记
   ```

4. **输出格式**：双模 — `--json`（Agent 用）和 表格/彩色文本（人用）

### Phase 3: Implementation

1. **Start with the data layer** — CSV/XLSX 解析，加载到内存 SQLite（启动时加载，后续查询走 SQL）

   ```python
   # core/data_loader.py
   def load_price_list(csv_path: str) -> List[Product]:
       """加载面价表 CSV 到内存"""
       products = []
       with open(csv_path, encoding='utf-8-sig') as f:
           reader = csv.DictReader(f)
           for row in reader:
               products.append(Product(
                   产品型号=row['产品型号'],
                   产品描述=row['产品描述'],
                   产品类型=row['产品类型'],
                   面价_pcs=float(row['面价/pcs']),
                   最小起订量=float(row['最小起订量']),
                   产品图片链接=row.get('产品图片链接', ''),
                   技术说明书链接=row.get('产品技术说明书链接', ''),
               ))
       return products
   ```

2. **Add search/filter commands** — 按型号精确查、按描述关键词模糊查、按参数结构化筛选

   ```python
   # core/search.py
   def search_by_model(products: List[Product], query: str) -> List[Product]:
       """按型号搜索（支持前缀和模糊）"""
       return [p for p in products if query.lower() in p.产品型号.lower()]

   def filter_by_specs(products: List[Product],
                        ip_rating: str = None,
                        current: str = None,
                        poles: str = None) -> List[Product]:
       """按参数筛选（解析产品描述中的 IP等级/电流/极数）"""
       results = products
       if ip_rating:
           results = [p for p in results if ip_rating in p.产品描述]
       if current:
           results = [p for p in results if current in p.产品描述]
       if poles:
           results = [p for p in results if poles in p.产品描述]
       return results
   ```

3. **Add pricing/quote commands** — 面价查询、折扣计算、报价单生成

   ```python
   # core/quote.py
   @dataclass
   class QuoteItem:
       product: Product
       quantity: int
       discount: float  # 折扣率，如 0.7 表示七折
       unit_price: float  # 面价 * 折扣
       subtotal: float    # unit_price * quantity

   def generate_quote(items: List[QuoteItem],
                       customer: str = "",
                       project: str = "") -> dict:
       """生成报价单"""
       return {
           "customer": customer,
           "project": project,
           "date": datetime.now().strftime("%Y-%m-%d"),
           "items": [asdict(i) for i in items],
           "total": sum(i.subtotal for i in items),
           "currency": "CNY",
       }
   ```

4. **Add session management** — Undo/Redo + 报价单暂存

5. **Add REPL** — 用 Click + prompt_toolkit 实现，类似 CLI-Anything 的 ReplSkin

6. **Backend abstraction** — 数据源可替换（CSV → 数据库 → API）

   ```python
   # backends/base.py
   class ProductBackend(ABC):
       @abstractmethod
       def load_products(self) -> List[Product]: ...

       @abstractmethod
       def load_stock(self) -> Dict[str, int]: ...

   # backends/csv_backend.py
   class CSVBackend(ProductBackend):
       """从本地 CSV/XLSX 文件加载数据"""

   # backends/api_backend.py
   class APIBackend(ProductBackend):
       """从远程 API 加载数据（未来扩展）"""
   ```

### Phase 4: Test Planning (TEST.md)

在写测试代码之前，先创建 TEST.md：

1. **Unit Test 计划**:
   - `test_data_loader.py`: CSV 解析、字段映射、编码处理、空行/异常行
   - `test_search.py`: 型号精确匹配、前缀匹配、模糊匹配、空结果
   - `test_filter.py`: 单条件筛选、多条件组合、IP等级解析、电流范围
   - `test_quote.py`: 单品报价、多品报价、折扣计算、最小起订量校验

2. **E2E Test 计划**:
   - 用真实面价表 CSV 跑完整查询流程
   - 用真实库存 XLSX 跑库存查询
   - CLI subprocess 测试（安装后完整链路）
   - 真实报价场景：数据中心客户要 200 个 IP67 63A 插头

3. **Agent Test** — 让 Claude Code 用 CLI 完成一个真实的销售场景

### Phase 5: Test Implementation

按 TEST.md 计划实现测试：

```bash
# 运行测试
cd SCAME-CLI && python -m pytest tests/ -v -s

# 强制使用安装版 CLI
SCAME_CLI_FORCE_INSTALLED=1 python -m pytest tests/ -v -s
```

### Phase 6.5: SKILL.md Generation

为 SCAME-CLI 生成 SKILL.md，让 Claude Code / 飞书机器人 / 企业微信机器人自动发现并调用：

```yaml
---
name: scame-cli
description: |
  SCAME 工业连接器产品查询与报价 CLI。支持按型号/参数/场景查询产品、
  生成报价单、查询库存。触发词：查产品、选型、报价、库存、SCAME、插头。
---
```

SKILL.md 包含：安装说明、命令文档、使用示例、Agent 使用指南（`--json` 模式）。

### Phase 7: 部署与集成

部署目标：

| 平台 | 集成方式 | 说明 |
|------|---------|------|
| Claude Code | Skill（SKILL.md） | 本地 CLI 直接调用 |
| 飞书机器人 | lark-cli Skill | 通过飞书消息触发查询 |
| 企业微信机器人 | Webhook | 接收消息 → 调 CLI → 返回结果 |
| 钉钉机器人 | Webhook | 同上 |

---

## Architecture Patterns

### 数据层分离

```
┌─────────────────────────────────────┐
│   SKILL.md (Agent 发现层)           │  触发词 + 命令文档
├─────────────────────────────────────┤
│   CLI 命令层 (Click 框架)           │  scame-cli <command>
├─────────────────────────────────────┤
│   Core 业务层                       │  search / filter / quote / recommend
├─────────────────────────────────────┤
│   Backend 数据层                    │  CSV / SQLite / API（可替换）
├─────────────────────────────────────┤
│   数据源                            │  面价表 CSV / 库存 XLSX / 知识库
└─────────────────────────────────────┘
```

**Backend 是唯一差异化点** — 当前用 CSV，未来切数据库或 API 只改 Backend 层。

### 面价解析规则

SCAME 产品描述遵循固定模式，可结构化解析：

```
PLUG 2P+E IP44 16A 4h 100-130V AC
│    │     │    │   │      │
│    │     │    │   │      └─ 电压范围
│    │     │    │   └─ 极数（小时制）
│    │     │    └─ 额定电流
│    │     └─ 防护等级
│    └─ 极数（国际标注）
└─ 产品类型（PLUG/SOCKET/COMBO/ PANEL）
```

```python
# core/spec_parser.py
import re

def parse_product_description(desc: str) -> dict:
    """从产品描述中提取结构化参数"""
    return {
        "type": _extract_type(desc),           # PLUG / SOCKET / INLET / COMBO
        "poles": _extract_poles(desc),          # 2P+E / 3P+E / 3P+N+E
        "ip_rating": _extract_ip(desc),         # IP44 / IP67
        "current": _extract_current(desc),      # 16A / 32A / 63A / 125A
        "voltage": _extract_voltage(desc),       # 100-130V / 200-250V / 380-415V
        "frequency": _extract_freq(desc),        # 50Hz / 60Hz
        "hours": _extract_hours(desc),           # 4h / 6h / 8h / 9h
    }
```

### 报价单生成规则

- 面价为 SCAME 官方定价（CNY/pcs）
- 折扣率根据客户等级和项目规模调整
- 最小起订量必须校验
- 报价单支持导出 CSV / Excel

### 查询缓存策略

- 面价表启动时全量加载到内存，变更频率低（季度更新）
- 库存数据按需加载（周更新），支持手动刷新

---

## Directory Structure

```
SCAME-CLI/
├── HARNESS.md                    ← 本文件（SOP + 架构文档）
├── README.md                     ← 使用说明
├── setup.py                      ← 包配置
├── scame_cli/                    ← 主包
│   ├── __init__.py
│   ├── __main__.py               ← python -m scame_cli
│   ├── cli.py                    ← Click 主入口 + REPL
│   ├── core/                     ← 业务逻辑
│   │   ├── __init__.py
│   │   ├── data_loader.py        ← 数据加载
│   │   ├── search.py             ← 搜索/筛选
│   │   ├── spec_parser.py        ← 产品参数解析
│   │   ├── quote.py              ← 报价生成
│   │   ├── recommend.py          ← 智能推荐
│   │   └── session.py            ← 会话管理 + Undo/Redo
│   ├── backends/                 ← 数据源后端（可替换）
│   │   ├── __init__.py
│   │   ├── base.py               ← 抽象基类
│   │   └── csv_backend.py        ← CSV/XLSX 后端
│   └── utils/                    ← 工具
│       ├── __init__.py
│       └── repl_skin.py          ← REPL 界面
├── tests/                        ← 测试
│   ├── TEST.md                   ← 测试计划 + 结果
│   ├── test_data_loader.py
│   ├── test_search.py
│   ├── test_filter.py
│   └── test_quote.py
├── data/                         ← 数据文件（symlink 或 copy）
│   └── README.md                 ← 数据源说明
├── skills/                       ← SKILL.md（Agent 发现）
│   └── scame-cli/
│       └── SKILL.md
└── examples/                     ← 使用示例
    └── sales_scenarios.md
```

---

## Principles & Rules

### 数据原则
- **面价表是 Single Source of Truth** — 所有价格查询必须基于面价表，不硬编码
- **产品描述可解析** — 所有结构化参数从描述中提取，不依赖额外标注
- **数据更新低摩擦** — 替换 CSV 即可更新产品线，不改代码

### CLI 设计原则
- **`--json` 双模输出** — 每个命令都支持人类可读和 JSON 两种输出
- **fail loudly** — Agent 需要明确错误信息（型号不存在、库存不足、起订量不够）
- **idempotent** — 重复查询安全，重复报价覆盖
- **introspection first** — `info`/`list`/`categories` 让 Agent 先观察再操作

### 业务原则
- **报价必须基于面价** — 不允许低于面价的报价（除非明确设置折扣）
- **起订量强制校验** — 数量低于起订量时报错
- **折扣可追溯** — 每次报价记录折扣率和理由

### Agent 集成原则
- **SKILL.md 自描述** — Agent 读文件就知道能做什么
- **结构化 JSON 输出** — Agent 直接解析，不依赖自然语言
- **Undo/Redo 支持** — 错误操作可回退
- **Session 持久化** — 跨命令保持上下文（选中产品、报价单）

---

## 产品参数解析参考

SCAME 产品描述的标准模式：

| 产品类型 | 示例描述 | 解析结果 |
|---------|---------|---------|
| 插头 (PLUG) | PLUG 2P+E IP44 16A 4h 200-250V AC | 2极+地, IP44, 16A, 4小时, 220V |
| 插座 (SOCKET) | SOCKET-OUTLET 3P+N+E IP67 32A 6h 380-415V AC | 4极, IP67, 32A, 6小时, 380V |
| 连接器 (COMBO) | COMBINATION 2P+E IP44 16A 4h 200-250V AC | 同插头但带插座组合 |
| 面板安装 (PANEL) | PANEL PLUG 3P+E IP67 63A 9h 380-415V AC | 面板安装式, 3极+地 |

防护等级含义：
- IP44: 防溅水，室内/工棚
- IP67: 防浸水，户外/港口/数据中心
- IP55: 防尘防喷水

额定电流 → 典型应用：
- 16A: 小功率设备、照明
- 32A: 中功率设备、空调
- 63A: 大功率设备、配电
- 125A: 超大功率、工业主线

---

## 应用场景映射

| 客户场景 | CLI 命令 | 示例 |
|---------|---------|------|
| 数据中心客户要插头 | `product filter --ip IP67 --current 63A` | 筛选 IP67 63A 产品 |
| 港口客户要替代品 | `recommend alternative --model 213.1630` | 找同规格更便宜型号 |
| 报价给客户 | `pricing quote --items '213.1630:50,C3444:30' --discount 0.75` | 生成报价单 |
| 查库存 | `stock check --model 213.1630` | 查实时库存 |
| 客户不知道要什么 | `recommend by-scenario --scenario 数据中心` | 按场景推荐 |
| 历史报价参考 | `pricing history --customer 中联` | 查该客户历史报价 |

---

## 下一步

1. 按 Phase 3 实现 CLI 骨架（data_loader + search + cli.py）
2. 加载面价表 CSV 验证数据解析
3. 实现核心查询命令
4. 生成 SKILL.md
5. 在 Claude Code 里测试完整销售场景
