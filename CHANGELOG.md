# Changelog

All notable changes to this project will be documented in this file.

## [0.3.2] - 2026-04-04

### Added
- 支持在 result_template 中使用公式计算
- 统一使用双层大括号语法 `{{}}`

### 语法

```yaml
# 简单取值
{{data.totalBalance}}

# 公式计算（内层替换后计算外层）
{{abs({data.totalBalance})/100}}
{{round({data.usage}/{data.limit}*100, 1)}}
```

### 支持的函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `abs(x)` | 绝对值 | `{{abs({data.balance})}}` |
| `round(x, n)` | 保留 n 位小数 | `{{round({data.usage}/{data.limit}*100, 1)}}` |
| `min()`, `max()` | 最大/最小值 | `{{min({data.a}, {data.b})}}` |
| `sqrt(x)` | 平方根 | `{{sqrt({data.value})}}` |
| `pow(x, n)` | 幂运算 | `{{pow({data.x}, 2)}}` |
| `floor()`, `ceil()` | 向下/向上取整 | `{{floor({data.value})}}` |

支持运算符：`+`, `-`, `*`, `/`, `%`（百分号自动转为 `/100`）

## [0.3.1] - 2026-04-03

### Added
- 初始版本
- 支持 YAML 配置模式
- 支持 LLM 工具调用