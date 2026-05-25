# Changelog

All notable changes to this project will be documented in this file.

## [1.2.1] - 2026-05-20

### 老铁速看666

对解析器配置进行较大改动，上个大版本仅支持YAML打字输入配置，而这次添加了可以手动选择的解析器

这次添加了选择器，在保持易用的同时兼容原版本的扩展性，你仍然可以配置自定义解析器来解析不常见的API格式

目前的内置解析器非常少，虽然代码里面写了一些但是全是未验证的（Deek整合的地址和方法）但是如果你们有经过验证的自定义请求体，你们可以附带代码和成功截图提出issue，我即会放入条目中

>     安装提示：请将老版本持久化数据完全删除后安装新版本，否则新版本配置项会失效
>     如果是意外升级，您仍然可以保留持久化数据降级回老版本，直到此分支加入正式版

<img width="300" height="348" alt="QQ_1779718660425" src="https://github.com/user-attachments/assets/52c788c9-d0b9-4402-aabf-82d4e6202fa0" />

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
