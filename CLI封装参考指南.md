# CLI 封装方法论 — 参考指南与实验手册

> 本文档总结 CLI-Anything（35.8k star）和飞书 CLI（11.2k star）的核心方法论，
> 作为 SCAME-CLI 项目的开发指南。所有实验结论将更新到本文档。

## 借鉴源头

### 核心借鉴（已深入分析）

| 项目 | GitHub | Star | 做了什么 | 我们抄什么 |
|------|--------|------|---------|-----------|
| **CLI-Anything** | https://github.com/HKUDS/CLI-anything | 35.8k | 把任意桌面软件包成 Agent 可调用的 CLI | 7 Phase 方法论、SKILL.md 发现机制、Backend 抽象层、Session+Undo |
| **飞书 CLI** | https://github.com/larksuite/cli | 11.2k | 把飞书 17 个业务域包成 CLI + 24 个 Agent Skill | 三层命令架构、`--json` 双模、Dry Run、Skill 注册机制 |

### 扩展借鉴（补充调研）

| 项目 | GitHub | Star | 做了什么 | 我们抄什么 |
|------|--------|------|---------|-----------|
| **Cobra** | https://github.com/spf13/cobra | 43.9k | Go CLI 框架（kubectl/GitHub CLI 底层） | `APP VERB NOUN --FLAG` 命令范式、嵌套子命令 + 级联 Flag、自动补全 + 智能纠错 |
| **OpenHands** | https://github.com/OpenHands/OpenHands | 73.9k | AI 开发 Agent 平台 | Agent-Tool 分离架构、Sandbox 安全模型、分级确认策略、TUI/CLI/Web 三模式入口 |
| **Textual** | https://github.com/Textualize/textual | 35.9k | Python TUI 框架 | 组件化声明式 UI、命令面板模糊搜索、`textual serve` 终端一键变 Web |
| **python-fire** | https://github.com/google/python-fire | 28.2k | 自动将 Python 函数/类变成 CLI | 零成本 CLI 化、自动发现方法签名思路、内置 REPL 模式 |
| **Bubbletea** | https://github.com/charmbracelet/bubbletea | 42.5k | Go TUI 框架（Elm Architecture） | Model-Update-View 单向数据流、Cmd 异步副作用、Bubbles+LipGloss 组件生态 |

---

## 一、背景：我们为什么研究 CLI 封装

### 1.1 问题的起源

韶聪有三重身份：

- **销售**：每周查几十次 SCAME 产品、做报价，靠翻 Excel
- **创业者**：做数字员工 SaaS（企微/飞书/钉钉机器人），核心是把业务能力封装给 AI Agent
- **个人**：40+ 个 Claude Code skills 用户，理解 Agent 生态

三个身份指向同一个需求：**把散落在各处的业务能力，封装成 AI Agent 能直接调用的标准化接口**。

### 1.2 发现 CLI-Anything

HKUDS/CLI-anything（35.8k star）做的事恰好是这个需求的通用解：

```
它的路径：任意桌面软件 → CLI 封装 → Agent 可调用
我们的路径：产品数据/业务流程 → CLI 封装 → 数字员工可调用
```

核心洞察：**CLI 是 Agent 最自然的接口 — 结构化、可发现、可组合、确定性**。

### 1.3 发现飞书 CLI

larksuite/cli（11.2k star）是飞书官方出的 CLI，做了同样的事：

```
飞书 17 个业务域（日历/消息/文档/表格/邮件...） → 200+ CLI 命令 → 24 个 Agent Skill
```

它验证了：**官方团队也在用 CLI 封装 + SKILL.md 发现机制这个模式**。

### 1.4 结论

两个项目，同一个模式，不同领域：

| 项目 | 封装对象 | Agent 接口 | Skill 机制 |
|------|---------|-----------|-----------|
| CLI-Anything | 桌面软件（GIMP/Blender） | Click CLI + `--json` | SKILL.md 自动生成 |
| 飞书 CLI | 飞书业务域（日历/消息） | 三层命令 + `--json` | 24 个 SKILL.md |
| **SCAME-CLI** | **产品数据/报价流程** | **Click CLI + `--json`** | **SKILL.md（待生成）** |

---

## 二、CLI-Anything 核心机制拆解

### 2.1 它到底做了什么

CLI-Anything **不运行 AI 模型**。它做的是纯工程：

1. 分析目标软件的源码/API/脚本接口
2. 设计一套 CLI 命令（命令组 + 参数 + 输出格式）
3. 用 Python Click 框架实现 CLI
4. 生成 SKILL.md 让 Agent 能发现这个 CLI
5. 打包到 PyPI，通过 CLI-Hub 分发

### 2.2 7 Phase 流水线

这是 CLI-Anything 的核心方法论（定义在 HARNESS.md 中）：

```
Phase 1: 分析源码
    → 找后端引擎（Blender 用 bpy、LibreOffice 用 headless）
    → 找数据模型（文件格式、状态结构）
    → 找已有 CLI（很多软件自带命令行工具）

Phase 2: 设计 CLI 架构
    → 定义命令组（project / core-ops / export / config / session）
    → 设计状态模型（什么需要跨命令保持？）
    → 设计输出格式（人读表格 + Agent 读 JSON）

Phase 3: 实现
    → data layer（解析项目文件）
    → probe/info 命令（让 Agent 先观察再操作）
    → mutation 命令（执行操作）
    → backend 集成（调用真实软件）
    → session 管理（Undo/Redo）
    → REPL 交互模式

Phase 4: 测试计划（TEST.md）
    → 先写计划，不写代码
    → 列出每个模块要测什么、多少个测试

Phase 5: 测试实现
    → 单元测试（mock 数据）
    → E2E 测试（调真实软件，验证输出文件）
    → CLI subprocess 测试（测安装后的命令）

Phase 6.5: SKILL.md 生成
    → 从 CLI 代码自动提取命令、参数、描述
    → 用 Jinja2 模板渲染 SKILL.md
    → 写入两个位置：skills/ 和包内

Phase 7: 发布
    → PyPI 打包
    → CLI-Hub 注册
```

### 2.3 关键抽象层

每个 CLI 适配器都遵循这个分层：

```
┌─────────────────────────────────┐
│   SKILL.md                      │  Agent 发现层：Agent 读这个文件知道能做什么
├─────────────────────────────────┤
│   CLI 命令层（Click 框架）       │  scame-cli <command> --json
├─────────────────────────────────┤
│   Core 业务层                   │  search / filter / quote / recommend
├─────────────────────────────────┤
│   Backend 后端层（可替换）       │  CSV / SQLite / API → 这是唯一差异化点
├─────────────────────────────────┤
│   数据源                        │  面价表 / 库存文件 / 远程 API
└─────────────────────────────────┘
```

**关键原则：Backend 是唯一差异化点**。上层命令统一，换数据源只改 Backend 层。

### 2.4 SKILL.md 发现机制

这是 CLI-Anything 最值得抄的设计：

**问题**：Agent 怎么知道有哪些 CLI 可以用？

**解法**：每个 CLI 自带一个 SKILL.md 文件，包含：
- YAML frontmatter（name + description）→ Agent 触发匹配
- 命令文档 → Agent 知道怎么调用
- 使用示例 → Agent 知道参数格式
- Agent 指南 → `--json` 模式、错误处理、返回码

**生成流程**（skill_generator.py）：
1. 扫描 CLI 包目录
2. 从 README.md 提取简介
3. 从 `_cli.py` 用正则解析 Click 装饰器 → 提取命令名 + docstring
4. 自动生成示例
5. 用 Jinja2 模板渲染
6. 写入 `skills/<skill-name>/SKILL.md`

### 2.5 状态管理（Session + Undo/Redo）

CLI-Anything 的 Session 设计：

```python
class Session:
    project: Dict[str, Any]     # 当前项目状态 (JSON)
    _undo_stack: List[Dict]     # undo 栈 (deep copy)
    _redo_stack: List[Dict]     # redo 栈
    _modified: bool             # 脏标记
```

- 每次修改前 `copy.deepcopy()` 做快照
- 50 层 undo 上限
- 文件锁（`fcntl.LOCK_EX`）防并发
- 自动保存（one-shot 命令退出时）

**对 SCAME-CLI 的迁移**：报价单编辑需要 Undo — 加了产品后悔了，undo 回去。

### 2.6 CLI-Anything 的局限

| 局限 | 说明 |
|------|------|
| 面向桌面软件 | 不直接适用 SaaS API / IM 平台 |
| 依赖源码分析 | 闭源软件无法自动生成 CLI |
| 无运行时 AI | 生成过程用 AI，运行时纯工程 |
| 学术项目风险 | 10 周 35k star，核心 1 人占 52% |

---

## 三、飞书 CLI 核心机制拆解

### 3.1 三层命令架构

```
Layer 1: Shortcuts（+前缀，人/AI 友好）
    lark-cli calendar +agenda
    lark-cli im +messages-send --chat-id "oc_xxx" --text "Hello"

Layer 2: API Commands（自动生成，与平台同步）
    lark-cli calendar calendars list
    lark-cli calendar events instance_view --params '...'

Layer 3: Raw API（全覆盖 2500+ API）
    lark-cli api GET /open-apis/calendar/v4/calendars
    lark-cli api POST /open-apis/im/v1/messages --data '...'
```

**对 SCAME-CLI 的启示**：
- Layer 1 = 快捷命令（`scame-cli search "IP67 63A"`）
- Layer 2 不需要（我们没有平台 API 要同步）
- Layer 3 = 原始 SQL 查询（高级用户直接查）

### 3.2 24 个 Skill 的设计模式

飞书 CLI 的每个 Skill 就是一个 SKILL.md + 对应的命令集：

```yaml
# lark-calendar SKILL.md（简化）
---
name: lark-calendar
description: 日程管理。查看/创建/更新日程、邀请参会者、查会议室。
触发词：日历、日程、agenda、calendar
---
```

安装方式：`npx skills add larksuite/cli -y -g`，一次性安装全部 24 个。

**对 SCAME-CLI 的启示**：一个 SKILL.md 覆盖所有产品查询+报价场景，不需要拆分。

### 3.3 飞书 CLI 的 OAuth + 身份体系

飞书 CLI 的身份模型：
- `--as user`：以用户身份操作（查自己的日历、发自己的消息）
- `--as bot`：以机器人身份操作（适合自动化场景）
- `auth status`：查看当前授权和权限范围

**对 SCAME-CLI 的启示**：当前不需要身份体系（本地 CLI），但未来做多用户版时需要。

### 3.4 Dry Run 模式

```bash
lark-cli im +messages-send --chat-id "oc_xxx" --text "test" --dry-run
```

不实际执行，只展示会发送什么。**非常适合报价场景**：先 dry-run 看报价单，确认后再真正生成。

---

## 四、方法论提炼：如何给任意东西写 CLI 封装

### 4.1 判断要不要封装

| 条件 | 封装 | 不封装 |
|------|------|--------|
| 有结构化接口（API/SDK/数据文件） | ✅ | |
| 重复使用频率高 | ✅ | |
| 当前只有 GUI/手动操作方式 | ✅ | |
| 已有现成 CLI 工具 | | ✅ 用现成的 |
| 纯人工流程，无可编程接口 | | ✅ 先数字化 |
| 一年用不到 3 次 | | ✅ 不值得 |

### 4.2 封装五步法

从 CLI-Anything 的 7 Phase 提炼出通用五步：

**Step 1：找后端接口**
- 桌面软件 → 找 CLI/脚本 API（blender --background、soffice --headless）
- SaaS → 找 REST API / SDK
- 数据文件 → 找解析库（csv、openpyxl、pandas）
- IM 平台 → 找 Open API（飞书/企微/钉钉都有）

**Step 2：设计命令空间**
- 定义 3-6 个命令组（不超过 7，Miller's Law）
- 每组 3-8 个命令
- 每个命令对应一个业务操作
- 必须有 `info`/`list` 类的观察命令（Agent 先看再操作）

**Step 3：实现分层架构**
```
SKILL.md（发现）→ CLI 命令（接口）→ Core（逻辑）→ Backend（数据源）
```
Backend 抽象基类 + 具体实现，保证数据源可替换。

**Step 4：双模输出**
- `--json`：Agent 用，结构化、可解析、包含完整信息
- 默认：人用，表格/彩色文本/省略细节
- 每个命令都必须支持两种模式

**Step 5：生成 SKILL.md**
- YAML frontmatter：name + description + 触发词
- 命令文档：每个命令的参数和输出
- 使用示例：3-5 个真实场景
- Agent 指南：`--json` 用法、错误处理、返回码含义

### 4.3 HARNESS.md 写法模板

HARNESS.md 是项目级别的 SOP 文档，告诉开发者（人或 AI）怎么给目标系统写 CLI 封装。

**必须包含的章节**：

```markdown
# [项目名] Harness: [目标系统] → Agent CLI

## Purpose
一句话说清楚这个 CLI 干什么。

## Phase 1: [目标系统]分析
- 数据源在哪？格式是什么？
- 有哪些可编程接口？
- 典型用户操作有哪些？

## Phase 2: CLI 架构设计
- 命令组划分
- 状态模型
- 输出格式

## Phase 3: Implementation
- 代码骨架
- 数据加载
- Backend 抽象
- Session 管理

## Phase 4-5: Test
- 测试计划
- 测试实现要求

## Phase 6.5: SKILL.md
- 生成方式
- 必须包含的内容

## Architecture Patterns
- 分层设计
- 后端抽象
- 状态管理
- 错误处理

## Directory Structure
标准目录布局。

## Principles & Rules
不可违反的规则清单。
```

### 4.4 SKILL.md 写法模板

```markdown
---
name: [skill-name]
description: |
  一句话定位。触发词包括但不限于：查产品、报价、库存、[关键词]。
  当用户提到 [相关场景] 时应触发。
  不要用于 [不适用场景]。
allowed-tools: Bash Read Write WebSearch
---

# [Skill Name]

[一句话说明这个 CLI 干什么]

## 安装
pip install [package-name]

## 命令

### [命令组1]
| 命令 | 说明 |
|------|------|
| `command1` | 说明 |
| `command2` | 说明 |

## 使用示例

### [场景1]
[描述]
[command]

### [场景2]
[描述]
[command]

## Agent 使用指南
1. 始终用 `--json` 获取结构化输出
2. 检查返回码：0=成功，非零=错误
3. 解析 stderr 获取错误信息
4. 用绝对路径指定文件
5. 操作后验证输出存在
```

---

## 五、SCAME-CLI 实验计划

### 实验 1：面价表加载与查询（验证数据层）

**目标**：证明 CSV 数据可以结构化加载并支持基本查询。

**步骤**：
1. 实现 `core/data_loader.py`：加载面价表 CSV 到 `List[Product]`
2. 实现 `core/spec_parser.py`：从产品描述解析出 IP 等级/电流/极数/电压
3. 实现 `core/search.py`：按型号精确查、按描述模糊查、按参数筛选
4. 写 `cli.py`：用 Click 注册 product search/filter 命令
5. 测试命令：`scame-cli product search "213.1630"`、`scame-cli product filter --ip IP67`

**验证标准**：
- 能加载全部产品记录
- 型号精确查命中率 100%
- 参数筛选能返回正确结果
- `--json` 输出可被 `jq` 解析

**预期耗时**：4-6 小时

### 实验 2：报价生成（验证业务层）

**目标**：证明可以基于面价表自动生成报价单。

**步骤**：
1. 实现 `core/quote.py`：QuoteItem 数据类、折扣计算、报价单生成
2. 实现 `cli.py` 的 pricing 命令组：price / quote / history
3. 测试：`scame-cli pricing quote --items "213.1630:50" --discount 0.75`
4. 输出格式：JSON（Agent 用）+ 表格（人用）

**验证标准**：
- 单品报价计算正确（面价 × 折扣 × 数量）
- 多品报价有合计
- 起订量校验生效（低于起订量报错）
- JSON 输出包含所有字段

**预期耗时**：3-4 小时

### 实验 3：SKILL.md 生成与 Claude Code 集成（验证发现层）

**目标**：证明 Claude Code 能通过 SKILL.md 自动发现并调用 SCAME-CLI。

**步骤**：
1. 编写 `skills/scame-cli/SKILL.md`
2. 将 SKILL.md 安装到 `~/.claude/skills/scame-cli/`
3. 在新对话中说"帮我查 IP67 63A 的 SCAME 插头"
4. 观察 Claude Code 是否自动调用 `scame-cli product filter`

**验证标准**：
- SKILL.md 触发词匹配成功
- Claude Code 能正确构造 CLI 命令
- 返回结果可读且准确

**预期耗时**：2-3 小时

### 实验 4：飞书集成（验证远程调用）

**目标**：证明飞书机器人可以远程调用 SCAME-CLI。

**步骤**：
1. 用 lark-cli 创建一个飞书机器人
2. 配置消息监听（lark-event Skill）
3. 收到消息 → 解析意图 → 调用 scame-cli → 返回结果
4. 测试：在飞书里发"查 213.1630 价格"

**验证标准**：
- 飞书消息触发 CLI 调用
- 结果在 3 秒内返回
- 支持中文自然语言查询

**预期耗时**：6-8 小时

### 实验 5：CLI-Anything 生成引擎复用（验证方法论可复制）

**目标**：证明 HARNESS.md 方法论可以指导另一个产品的 CLI 封装。

**步骤**：
1. 选一个其他产品线（如配电箱产品数据）
2. 严格按 HARNESS.md 的 Phase 1-6.5 执行
3. 记录每个 Phase 的耗时和遇到的问题
4. 对比 SCAME-CLI 的开发经验，提炼通用流程

**验证标准**：
- 第二个产品的 CLI 开发时间 < 第一个的 50%
- HARNESS.md 的指导足够清晰，不需要额外解释

**预期耗时**：4-6 小时

---

## 六、开发流程与规范

### 6.1 开发流程

```
1. 读 HARNESS.md 的对应 Phase
2. 实现（TDD：先写测试再写代码）
3. 本地验证（python -m scame_cli <command>）
4. Agent 验证（Claude Code 通过 SKILL.md 调用）
5. 更新项目开发日志
```

### 6.2 代码规范

- CLI 入口：Click 框架，`@click.group` + `@click.command`
- 每个 command 都支持 `--json` flag
- Backend 抽象基类：`class Backend(ABC)`
- 错误信息要明确（Agent 靠 stderr 自我修正）
- Session 状态用 JSON 文件持久化

### 6.3 测试规范

- 单元测试：`tests/test_*.py`，mock 数据
- E2E 测试：用真实面价表 CSV
- CLI subprocess 测试：测安装后的命令
- 测试命令：`python -m pytest tests/ -v -s`

### 6.4 Git 规范

- 分支：`main`（稳定）+ `dev`（开发）
- Commit：Conventional Commits（feat/fix/docs/test）
- 不自动 push

---

## 七、技术架构

### 7.1 整体架构

```
                    ┌──────────────┐
                    │  SKILL.md    │  Agent 发现入口
                    └──────┬───────┘
                           │ Agent 读取后构造命令
                    ┌──────▼───────┐
                    │  cli.py      │  Click 命令入口
                    │  + REPL      │  交互模式
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──┐  ┌──────▼──┐  ┌──────▼──┐
       │ product │  │ pricing │  │ stock   │  命令组
       │ search  │  │ quote   │  │ check   │
       │ filter  │  │ price   │  │ avail   │
       └──────┬──┘  └──────┬──┘  └──────┬──┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼───────┐
                    │  Backend     │  数据源抽象层
                    │  CSVBackend  │  ← 当前实现
                    │  SQLiteBknd  │  ← 未来扩展
                    │  APIBackend  │  ← 未来扩展
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──┐  ┌──────▼──┐  ┌──────▼──┐
       │ 面价表  │  │ 库存表  │  │ 历史报价│  数据源
       │ CSV     │  │ XLSX    │  │ CSV     │
       └─────────┘  └─────────┘  └─────────┘
```

### 7.2 数据流

**查询场景**：
```
用户/Agent: "IP67 63A 插头"
  → cli.py: product filter --ip IP67 --current 63A --json
    → search.py: filter_by_specs(ip="IP67", current="63A")
      → data_loader.py: 从内存中查 List[Product]
        → spec_parser.py: 解析每条产品描述的参数
          → 返回匹配产品
    → JSON 输出: [{"型号":"xxx", "面价":xxx, ...}]
```

**报价场景**：
```
用户/Agent: "50个213.1630，七折"
  → cli.py: pricing quote --items "213.1630:50" --discount 0.75 --json
    → quote.py: 查面价 → 算折扣 → 校验起订量 → 生成报价单
    → JSON 输出: {"items":[...], "total":xxx, "currency":"CNY"}
```

### 7.3 Backend 抽象

```python
class ProductBackend(ABC):
    @abstractmethod
    def load_products(self) -> List[Product]: ...

    @abstractmethod
    def load_stock(self) -> Dict[str, int]: ...

    @abstractmethod
    def load_history(self) -> List[Quote]: ...

class CSVBackend(ProductBackend):
    """当前实现：从本地 CSV/XLSX 加载"""

class SQLiteBackend(ProductBackend):
    """未来：产品数据入库，查询更快"""

class APIBackend(ProductBackend):
    """未来：从 ERP / CRM 系统实时拉数据"""
```

### 7.4 spec_parser 设计

SCAME 产品描述遵循固定模式，可以结构化解析：

```
输入: "PLUG 2P+E IP44 16A 4h 100-130V AC"
输出: {
    "type": "PLUG",        # 产品类型
    "poles": "2P+E",       # 极数
    "ip_rating": "IP44",   # 防护等级
    "current": "16A",      # 额定电流
    "hours": "4h",         # 小时制
    "voltage": "100-130V", # 电压范围
    "ac_dc": "AC"          # 交直流
}
```

解析规则：
- type: 正则 `^(PLUG|SOCKET|INLET|COMBO|PANEL)\b`
- ip_rating: 正则 `IP\d{2}`
- current: 正则 `\d+A`
- poles: 正则 `\d+P(?:\+\w+)*` 或 `\d+h`

---

## 八、从 CLI-Anything 和飞书 CLI 学到的经验

### 8.1 方法论可迁移

CLI-Anything 证明了：**"分析 → 设计 → 实现 → 测试 → 发现 → 发布"这个流水线适用于任何"把东西包成 Agent 接口"的场景**。

我们的迁移路径：
- 桌面软件 → 产品数据（Backend 从 subprocess 变成 CSV 解析）
- GUI 操作 → 产品查询（命令从"加图层"变成"按参数筛选"）
- 文件导出 → 报价单生成（从"渲染图片"变成"计算折扣"）

### 8.2 SKILL.md 是 Agent 生态的关键基础设施

没有 SKILL.md，Agent 不知道有什么工具可用。有了 SKILL.md：
- Claude Code 自动发现并调用
- 飞书机器人通过 Skill 机制调用
- 未来任何支持 Skill 的 Agent 都能用

**这是标准化接口的价值：写一次，所有 Agent 都能用。**

### 8.3 `--json` 双模输出是必须的

人用 CLI 要表格和颜色。Agent 用 CLI 要结构化 JSON。

CLI-Anything 的做法：每个 Click 命令检查 `--json` flag，走不同格式化路径。这个模式直接复用。

### 8.4 Undo/Redo 在业务场景很重要

CLI-Anything 给桌面软件做了 50 层 Undo。SCAME-CLI 的报价场景也需要：
- 加了一个产品想撤回
- 折扣打错了想改
- 整个报价单想重来

### 8.5 Backend 抽象让产品可持续

CLI-Anything 从 Pillow（轻量）升级到 GIMP 原生引擎时，只改了 Backend 层。

SCAME-CLI 从 CSV 升级到数据库/ERP API 时，同样只改 Backend 层。**这个抽象层是长期投资。**

### 8.6 不要重复造轮子

飞书已经有 lark-cli，不要自己写飞书 API 封装。

SCAME-CLI 的定位是：**产品数据 + 报价流程**的 CLI 封装，不是通用 IM 平台封装。飞书集成用 lark-cli，企微/钉钉用官方 SDK。

### 8.7 命令命名要用自然语序（来自 Cobra）

Cobra 被 kubectl、GitHub CLI、Hugo 等大量知名项目采用，核心命令范式：

```
APP VERB NOUN --FLAG
```

应用到 SCAME-CLI：
```
scame search product --ip IP67           # 查产品
scame create quote --customer 中联       # 建报价
scame check stock --model 213.1630       # 查库存
```

比 `scame-cli product search` 更像自然语言。但考虑到 SCAME-CLI 已用 Click + 命令组模式，保持当前 `scame-cli product search` 也可接受，两者不矛盾。

**更值得抄的是 Cobra 的自动补全和智能纠错**：输入 `scame-cli prodcut` 自动建议 "did you mean product?"。对非技术用户（销售人员）很友好。

### 8.8 CLI 入口要支持三模式（来自 OpenHands）

OpenHands 的入口设计：

```bash
openhands          # 默认：TUI 交互界面
openhands --headless  # 纯 CLI 模式（脚本/Agent 用）
openhands serve    # Web 服务器模式（远程访问）
```

SCAME-CLI 照搬这个设计：

```bash
scame-cli                # 默认：交互式 REPL
scame-cli --headless product search "213.1630"  # 纯 CLI（Agent/脚本用）
scame-cli serve          # Web API 模式（飞书机器人调）
```

**关键洞察**：Agent 调用 `--headless` 模式拿到纯 JSON，人用默认模式看到彩色表格，远程调用 `serve` 模式走 HTTP。同一套 Core 逻辑，三种入口。

### 8.9 敏感操作要分级确认（来自 OpenHands）

OpenHands 定义了 4 级确认策略：

| 策略 | 行为 | 适用场景 |
|------|------|---------|
| AlwaysConfirm | 每次操作都问 | 新用户、高风险环境 |
| ConfirmRisky | 只在风险操作时问 | 正常使用 |
| NeverConfirm | 从不确认 | CI/CD、自动化 |
| LLMApprove | AI 判断是否需要确认 | Agent 自主决策 |

SCAME-CLI 的报价场景直接适用：

- 查询产品 → NeverConfirm（只读，无风险）
- 生成报价单 → ConfirmRisky（涉及折扣、金额）
- 发送报价给客户 → AlwaysConfirm（不可逆操作）

### 8.10 终端可以一键变 Web（来自 Textual）

Textual 的 `textual serve` 一行命令把终端应用变成浏览器应用。

对 SCAME-CLI 的意义：如果客户不想装 Python/CLI，`scame-cli serve` 起一个 Web 界面，浏览器打开就能用。**这是从 CLI 工具到 SaaS 产品的最小桥梁。**

### 8.11 自动 CLI 生成可以加速原型（来自 python-fire）

Google 的 python-fire 做到一行代码把 Python 类变成 CLI：

```python
import fire

class ProductCLI:
    def search(self, keyword: str):
        """按关键词搜索产品"""
        return [p for p in products if keyword in p.产品描述]

    def filter(self, ip: str = None, current: str = None):
        """按参数筛选"""
        ...

fire.Fire(ProductCLI)
```

自动变成：`python cli.py search --keyword "IP67"`

**局限**：不支持命令分组、flag 验证差、无自动补全。不适合产品级 CLI。

**但值得借鉴的思路**：用函数签名自动生成 Agent tool 注册。SCAME-CLI 的 SKILL.md 生成器可以类似地扫描 Backend 方法签名，自动生成命令文档。

### 8.12 单向数据流避免状态混乱（来自 Bubbletea）

Bubbletea 采用 Elm Architecture：

```
Model（状态） → Update（处理事件，返回新状态） → View（渲染 UI）
```

所有状态变更都是**纯函数**，不直接修改 Model。这在 SCAME-CLI 的复杂报价流程中很有用：
- 多个产品加入报价单
- 折扣修改影响总价
- Undo/Redo 需要状态回溯

如果用 Bubbletea 的模式，每次操作返回新的报价单状态（而非修改原状态），Undo 就是回到上一个状态快照。**这和 CLI-Anything 的 deepcopy 快照是同一思路，但 Bubbletea 的实现更优雅。**

---

## 九、数字员工 SaaS 的复用路径

### 9.1 从 SCAME-CLI 到通用产品

SCAME-CLI 验证的是一套方法论。验证成功后：

```
SCAME-CLI（验证方法）→ 客户 A 的产品 CLI → 客户 B 的报价 CLI → ...
```

每个客户的封装 = 一次 HARNESS.md 流水线执行 = 一个数字员工能力。

### 9.2 标准化交付物

给客户交付的标准化产出：

| 交付物 | 说明 | 来源 |
|--------|------|------|
| HARNESS.md | 该客户的 CLI 封装 SOP | 基于 CLI-Anything 模板定制 |
| CLI 代码 | 可运行的命令行工具 | 按 HARNESS.md Phase 3 实现 |
| SKILL.md | Agent 发现文件 | 按 Phase 6.5 生成 |
| 测试报告 | TEST.md + pytest 输出 | 按 Phase 4-5 |
| 集成方案 | 飞书/企微/钉钉机器人对接 | 按实验 4 的经验 |

### 9.3 定价逻辑

- 基础封装（1 个数据源 + 查询 + SKILL.md）：按项目定价
- 高级封装（多数据源 + 报价 + 自动化）：按项目 + 月费
- 定制 Skill 开发：按时计费

---

## 十、参考资料

### 核心借鉴

| 资料 | 位置 |
|------|------|
| CLI-Anything 仓库 | https://github.com/HKUDS/CLI-anything |
| 飞书 CLI 仓库 | https://github.com/larksuite/cli |
| CLI-Anything HARNESS.md（原文） | 已安装到 `~/.claude/plugins/cache/cli-anything/HARNESS.md` |
| CLI-Anything skill_generator.py | 已安装到 `~/.claude/plugins/cache/cli-anything/skill_generator.py` |
| CLI-Anything SKILL.md 模板 | 已安装到 `~/.claude/plugins/cache/cli-anything/templates/SKILL.md.template` |
| 飞书 CLI 云文档 | https://www.feishu.cn/file/QpHdb4eOvo4N6axyyUncN5STnie |
| GitHub 分析报告（larksuite/cli） | `00_全局资产/github-analyses/2026-05-18-larksuite-cli.md` |
| GitHub 分析报告（CLI-anything） | `00_全局资产/github-analyses/2026-05-18-HKUDS-CLI-anything.md` |
| SCAME-CLI HARNESS.md | `SCAME-CLI/HARNESS.md` |

### 扩展借鉴

| 资料 | 位置 | 借鉴点 |
|------|------|--------|
| Cobra（Go CLI 框架） | https://github.com/spf13/cobra | 命令范式、级联 Flag、自动补全、智能纠错 |
| OpenHands（AI Agent 平台） | https://github.com/OpenHands/OpenHands | Agent-Tool 分离、Sandbox 安全、分级确认、TUI/CLI/Web 三模式 |
| Textual（Python TUI） | https://github.com/Textualize/textual | 命令面板、`textual serve` 终端变 Web |
| python-fire（自动 CLI） | https://github.com/google/python-fire | 零成本 CLI 化、函数签名自动发现 |
| Bubbletea（Go TUI） | https://github.com/charmbracelet/bubbletea | Elm Architecture 单向数据流、异步 Cmd 模式 |

---

## 十一、经验如何应用到 SCAME 销售项目

### 11.1 当前痛点

| 痛点 | 现状 | CLI 封装后 |
|------|------|-----------|
| 查产品参数 | 打开 Excel，Ctrl+F 搜索 | `scame-cli product search "213.1630"` 1 秒出结果 |
| 按需求选型 | 凭经验翻产品目录 | `scame-cli product filter --ip IP67 --current 63A` 自动筛选 |
| 做报价单 | 手动填 Excel 模板，容易算错 | `scame-cli pricing quote --items "213.1630:50" --discount 0.75` 秒出 |
| 查库存 | 找最新 XLSX，手动查找 | `scame-cli stock check --model "213.1630"` |
| 找替代品 | 脑子里记型号，记不全 | `scame-cli recommend alternative --model "213.1630"` |
| 客户随口问价 | 掏手机翻 Excel，客户等着 | 飞书/企微里直接问，Agent 秒回 |

### 11.2 SCAME-CLI 的三个使用层级

**层级 1：本地 Claude Code（现在就能用）**

```
你在 Claude Code 里说：
  "客户要 IP67 的 63A 插头，帮我查一下"
Claude Code 读 SKILL.md → 调用 scame-cli product filter --ip IP67 --current 63A --json
  → 返回产品列表 + 面价
你说：
  "给他报个价，50 个，七折"
Claude Code → 调用 scame-cli pricing quote --items "C3444:50" --discount 0.75 --json
  → 返回报价单 JSON
```

**层级 2：飞书机器人（实验 4 完成后可用）**

```
客户在飞书群里发消息：
  "韶聪，213.1630 多少钱？"
飞书机器人收到 → 解析意图 → 调用 scame-cli pricing price --model "213.1630" --json
  → 回复：面价 78 元/个，最小起订量 10 个

客户接着说：
  "要 50 个，能优惠吗？"
飞书机器人 → 调用 scame-cli pricing quote --items "213.1630:50" --discount 0.75 --json
  → 回复报价单
```

**层级 3：企业微信/钉钉机器人（数字员工 SaaS 产品化后）**

```
任何客户在自己的企业微信里：
  发消息给"SCAME 选型助手" → 后台调 scame-cli → 返回结果
这就是你卖的产品。
```

### 11.3 从 CLI-Anything 借鉴的关键设计

| CLI-Anything 设计 | SCAME-CLI 对应 | 业务价值 |
|------------------|----------------|---------|
| SKILL.md 发现机制 | `skills/scame-cli/SKILL.md` | Agent 自动发现产品查询能力，不需要硬编码 |
| `--json` 双模输出 | 每个命令都支持 | 人看表格，Agent 解析 JSON，同一个 CLI 服务两边 |
| Backend 抽象 | `CSVBackend → SQLiteBackend → APIBackend` | 先用 CSV 快速启动，未来接 ERP 无缝迁移 |
| Session + Undo/Redo | 报价单编辑可撤销 | 报价过程中加错产品可以 undo，不会从头来 |
| Dry Run（飞书 CLI） | `scame-cli pricing quote ... --dry-run` | 先预览报价单，确认后再真正生成/发送 |
| 7 Phase 流水线 | HARNESS.md 定义完整 SOP | 任何新业务数据都能按同样流程封装 |

### 11.4 具体开发路线

```
Phase 1（本周）：面价表加载 + 查询命令
  → 数据层跑通，能查产品、能按参数筛选
  → 实验 1

Phase 2（本周）：报价命令
  → 能生成报价单、校验起订量、算折扣
  → 实验 2

Phase 3（本周）：SKILL.md + Claude Code 集成
  → 在 Claude Code 里直接用自然语言查产品
  → 实验 3

Phase 4（下周）：飞书机器人集成
  → 在飞书群里用 scame-cli 回复客户查询
  → 实验 4

Phase 5（下周）：库存查询 + 历史报价
  → 接入库存 XLSX 和历史报价 CSV
  → 丰富数据源

Phase 6（持续）：配电箱产品线扩展
  → 按 HARNESS.md 方法论封装配电箱数据
  → 验证方法论可复制性（实验 5）
```

---

## 十二、经验如何应用到数字员工 SaaS 项目

### 12.1 核心洞察

CLI-Anything 卖的不是工具，是方法论。飞书 CLI 卖的不是 CLI，是 Agent-Native 的业务接口。

**你要卖的也不是 CLI，是"帮客户把业务能力变成数字员工"的服务。**

```
CLI-Anything 的交付物：
  HARNESS.md + CLI 代码 + SKILL.md + 测试

你的交付物（一模一样的结构）：
  IM-Anything HARNESS.md + IM Skill 代码 + SKILL.md + 测试 + 机器人部署
```

### 12.2 产品架构：从 SCAME-CLI 到 IM-Anything

SCAME-CLI 验证了数据层 → CLI 层 → Skill 层这条链路。数字员工 SaaS 在此基础上加一个 IM 层：

```
┌───────────────────────────────────────────────────┐
│   IM 层（飞书 / 企微 / 钉钉机器人）               │  客户看到的界面
│   收消息 → 解析意图 → 调 CLI → 格式化回复          │
├───────────────────────────────────────────────────┤
│   SKILL.md 层                                      │  Agent 发现入口
│   每个数字员工能力一个 SKILL.md                     │
├───────────────────────────────────────────────────┤
│   CLI 层                                           │  业务接口
│   scame-cli / client-a-cli / client-b-cli          │
├───────────────────────────────────────────────────┤
│   Backend 层                                       │  数据源（可替换）
│   CSV / 数据库 / ERP API / CRM API                 │
└───────────────────────────────────────────────────┘
```

### 12.3 给每个客户做封装的标准流程

借鉴 CLI-Anything 的 7 Phase，定制为数字员工版：

```
Phase 1: 客户业务分析
  → 客户用什么系统管产品/库存/客户？
  → 有 API 吗？有结构化数据文件吗？
  → 客户的典型业务操作有哪些？（查询、报价、下单、跟进）

Phase 2: 设计数字员工能力
  → 定义 Skill 命令组（产品查询、报价、客户跟进...）
  → 设计 SKILL.md（触发词、命令文档）
  → 设计输出格式（文本/卡片/链接）

Phase 3: 实现 CLI + Backend
  → Backend 封装客户的数据源
  → CLI 命令实现业务逻辑
  → 双模输出（JSON 给 Agent，文本给客户）

Phase 4-5: 测试
  → 用客户真实数据跑测试
  → Agent 测试：让 Claude 模拟客户提问

Phase 6: IM 集成
  → 选平台（飞书/企微/钉钉）
  → 部署机器人
  → 消息监听 → 意图解析 → CLI 调用 → 回复

Phase 7: 交付 + 维护
  → 交付 HARNESS.md + 代码 + SKILL.md
  → 培训客户使用
  → 月度维护（数据更新、新能力扩展）
```

### 12.4 借鉴飞书 CLI 的三层命令到 IM 场景

```
Layer 1: 快捷命令（客户直接说人话）
  客户："查一下 IP67 的 63A 插头"
  → 后台调 product filter --ip IP67 --current 63A

Layer 2: API 命令（高级用户/管理员）
  管理员发命令："/product filter --ip IP67 --current 63A"
  → 直接映射到 CLI 命令

Layer 3: Raw API（开发者调试）
  开发者：直接调 CLI 或 HTTP API
  → scame-cli product filter --ip IP67 --current 63A --json
```

### 12.5 借鉴 CLI-Anything 的生成引擎

CLI-Anything 最强的能力是：**给一个软件源码，自动生成完整的 CLI 适配器**。

迁移到数字员工场景：

```
CLI-Anything：给软件源码 → 自动生成 CLI wrapper
IM-Anything：给客户的 API 文档/数据文件 → 自动生成数字员工 Skill
```

**具体实现**：
1. 客户提供 ERP/CRM 的 API 文档（OpenAPI spec / 文字说明）
2. 改造 CLI-Anything 的 `/cli-anything` 命令，变成 `/generate-skill`
3. AI 自动分析 API → 生成 Backend 封装 + CLI 命令 + SKILL.md
4. 人工微调 → 部署到飞书/企微

**这就是你产品的核心卖点：客户说需求，AI 自动生成数字员工。**

### 12.6 定价模型（参考 CLI-Anything 的 Hub 模式）

CLI-Anything 有 CLI-Hub（包管理器），社区贡献和安装 CLI 适配器。

你的数字员工 SaaS 可以有类似的"Skill 市场"：

| 层级 | 内容 | 定价 |
|------|------|------|
| 免费层 | 通用 Skill 模板（产品查询、报价等） | 开源/免费 |
| 基础层 | 按客户数据定制 Skill | 一次性项目费 |
| 高级层 | 多数据源 + 自动化 + 监控 | 月费 |
| 市场层 | 客户自建 Skill 上架分享 | 抽佣 |

### 12.7 从 SCAME-CLI 验证到 SaaS 产品化的路径

```
现在：SCAME-CLI（Phase 1-3 实验）
  验证：数据加载、查询、报价、SKILL.md 集成

下一步：配电箱 CLI（Phase 6）
  验证：HARNESS.md 方法论对另一个产品线也适用

再下一步：找第一个付费客户
  用同样的方法论，帮客户封装他们的业务数据

最终：IM-Anything 平台
  自动生成引擎 + Skill 市场 + 多 IM 平台部署
```

### 12.8 关键风险与应对

| 风险 | 来源 | 应对 |
|------|------|------|
| 客户数据格式不统一 | SCAME-CLI 实验中会发现 | spec_parser 做得足够通用，覆盖变体 |
| 客户没有 API | 小微企业数字化程度低 | 先用文件导入（CSV/Excel），Backend 抽象保证未来可升级 |
| IM 平台限制 | 飞书/企微/钉钉各有差异 | IM 层也做抽象（IMBackend），上层 Skill 统一 |
| 客户不愿付费 | 数字员工是新概念 | SCAME-CLI 先跑通自己的业务，用效果说服客户 |
| CLI-Anything 团队放弃 | 学术项目，核心 1 人 | 不依赖它的代码，只借鉴方法论 |

---

## 十三、本文件维护规则

- 每完成一个实验，在"五、实验计划"中标记 ✅ 并补充结论
- 发现新的可借鉴设计时，追加到对应章节
- 遇到坑时，在"八、经验"中追加
- 项目开发日志记录进度，本文件记录方法论

---

*最后更新: 2026-05-18*
