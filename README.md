# SCAME-CLI

SCAME 工业连接器产品查询与报价命令行工具。

## 快速开始

```bash
# 安装依赖
pip install -e .

# 查询产品
scame-cli product search "213.1630"

# 按参数筛选
scame-cli product filter --ip IP67 --current 63A

# 生成报价
scame-cli pricing quote --items "213.1630:50,C3444:30" --discount 0.75

# JSON 输出（Agent 模式）
scame-cli --json product filter --ip IP67 --current 63A

# 交互式 REPL
scame-cli
```

## 数据源

面价表 CSV 位于 `data/` 目录（symlink 到原始数据）：

```bash
# 首次设置：创建数据目录并链接面价表
mkdir -p data
ln -s "/path/to/2026_SCAME_面价表_包含选型型号.csv" data/price_list.csv
```

## 命令

| 命令组 | 说明 |
|--------|------|
| `product search/filter/info/compare` | 产品查询 |
| `pricing price/quote/history` | 报价管理 |
| `stock check/available` | 库存查询 |
| `recommend by-scenario/alternative` | 智能推荐 |
| `catalog categories/export` | 产品目录 |

## 架构

详见 [HARNESS.md](HARNESS.md)。

---

<div align="center">

**韶聪泽明 · 班底 Zecrew**

北京韶聪泽明智能科技有限责任公司

企业数字员工 · 企业 AI 落地服务 · FDE

WaytoAGI 模数OPC 社区

官网 [zecrew.shaocongzeming.com](https://zecrew.shaocongzeming.com) · 邮箱 [sunshaocong@shaocongzeming.com](mailto:sunshaocong@shaocongzeming.com)

</div>
