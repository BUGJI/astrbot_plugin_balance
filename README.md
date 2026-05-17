# 💴万能余额查询

AstrBot 万能余额查询，只需要详细填写配置文件即可

优势：
- 支持99%的余额请求格式
- 内置解析器：常用服务开箱即用，只需填 api_key
- 配置中任意一行失败，不影响其他行
- 支持LLM请求（可开关）
- 支持YAML配置，更灵活，支持URL参数、复杂Header、多结果展示
- 可选择使用旧版或新版配置

# 👉快速开始

使用```balance```命令，则会返回如下格式的消息：
```
余额查询结果：
A云 1.14 元
B云 5.14 元
```

## 📕模板配置

插件支持两种配置方式：旧版配置（单行文本）和新版YAML配置（更灵活配置）。

请在插件配置中勾选"使用新版YAML配置"来选择配置方式。

建议新用户使用```新版YAML配置```，对于旧版有更强的可操作性。

### 🚀 内置解析器（v0.4.0 新增）

只需 `type` + `api_key`，无需手动找 API 地址和 JSON 路径。

```yaml
services:
  deepseek:
    type: "deepseek"
    api_key: "sk-xxx"

  siliconflow:
    type: "siliconflow"
    api_key: "sk-xxx"

  openrouter:
    type: "openrouter"
    api_key: "sk-or-xxx"

  moonshot:
    type: "moonshot"
    api_key: "sk-xxx"

  openai:
    type: "openai"
    api_key: "sk-xxx"

  # One-API / New-API 自建实例（需要 base_url）
  my_api:
    type: "oneapi"
    base_url: "https://my-api.example.com"
    api_key: "sk-xxx"
```

**当前支持的内置类型：** `deepseek`, `siliconflow`, `openrouter`, `oneapi`, `moonshot`, `openai`

内置模式下，用户仍可选择性覆盖 `url`、`headers`、`result_template`、`display_name`、`method` 字段。

### YAML 自定义模式

`type: "custom"` 或不填 `type` 时使用自定义模式，需完整配置 url/headers/result_template。

```yaml
services:
  Deepseek:
    type: "custom"  # 可不填，默认 custom
    url: "https://api.deepseek.com/user/balance"
    headers:
      Accept: "application/json"
      Authorization: "Bearer Your-APIKEY"
    result_template: "Deepseek: {{balance_infos.0.total_balance}} 元"

  SiliconFlow:
    url: "https://api.siliconflow.cn/v1/user/info"
    headers:
      Authorization: "Bearer Your-APIKEY"
      Content-Type: "application/json"
    result_template: "SiliconFlow: {{data.totalBalance}} 元"
```

### 单行配置

你可以直接粘贴至配置文件，只需要替换您账户的有效token即可（一行一个）

```
OneThingAI 网心云|https://api-lab.onethingai.com/api/v1/account/wallet/detail|Authorization: Bearer 你的token|data.availableBalance|元
硅基流动 哈基流动|https://api.siliconflow.cn/v1/user/info|Authorization: Bearer 你的token|data.totalBalance|元
Deepseek 蓝色鲸鱼|https://api.deepseek.com/user/balance|Authorization: Bearer 你的token|balance_infos.0.total_balance|元
百度 不确定能不能调用|https://billing.baidubce.com/v1/finance/cash/balance|Authorization: 你的token|cashBalance|元
```

## 🔍解读配置

### YAML配置

| 项目 | 用途 |
| ---- | ---- |
| display_name | 自定义展示名称（可选，默认使用key） |
| url | 请求地址，支持URL参数 |
| headers | 请求头，键值对形式，支持特殊字符 |
| method | 请求方法（可选，默认GET） |
| result_template | 结果模板，使用 `{{path}}` 替换，支持公式计算 |

### 模板语法

使用 **双层大括号** `{{}}` 包裹内容：

```yaml
# 简单取值
result_template: "{{data.totalBalance}} 元"

# 公式计算（内层 {path} 替换后计算外层）
result_template: "{{abs({data.totalBalance})/100}} 元"
result_template: "{{round({data.usage}/{data.limit}*100, 1)}}%"
```

**支持的函数：**

| 函数 | 说明 | 示例 |
|------|------|------|
| `abs(x)` | 绝对值 | `{{abs({data.balance})}}` |
| `round(x, n)` | 保留 n 位小数 | `{{round({data.usage}/{data.limit}*100, 1)}}` |
| `sqrt(x)` | 平方根 | `{{sqrt({data.value})}}` |
| `pow(x, n)` | 幂运算 | `{{pow({data.x}, 2)}}` |
| `floor()`, `ceil()` | 取整 | `{{floor({data.value})}}` |

支持运算符：`+`, `-`, `*`, `/`, `%`（如 `50%` = `50/100`）

### 单行配置

配置项以```|```符号分割，一行一个，格式如下：

```备注|请求地址|请求头|要读取的字段名|金额单位```

| 项目 | 用途 |
| ---- | ---- |
| 备注 | 用于显示API服务商名字 |
| 请求地址 | 即显式API地址，通常http(s)开头 |
| 请求头 | 即填写密钥头的地址，通常为Authorization: Bearer xxxxxx |
| 要读取的字段名 | 通常余额会返回json格式，自动匹配余额字段并且获取余额 |
| 单位 | 一个自定义后缀，通常写 元、积分 |

# 💩添加第三方配置

它支持大部分已提供api的服务商，并且格式大差不差

如这是网心AI的默认请求方式：

curl 请求例子：
```bash
curl 'https://api-lab.onethingai.com/api/v1/account/wallet/detail' -H 'Authorization: Bearer {TOKEN}'
```
返回例子：
```json
{
    "code": 0,
    "msg": "Success",
    "data": {                    #这里有个data配置节
      "availableBalance": 0.05,  #假设这一项是余额
      "availableVoucherCash": 72.93,  
      "consumeCashTotal": 6,          
    }
}
```

假设你的token是123456，那么应将配置写为：

```text
网心云|https://api-lab.onethingai.com/api/v1/account/wallet/detail|Authorization: Bearer 123456|data.availableBalance|元
```

或者新的yaml格式：

```yaml
  OneThing:
    url: "https://api-lab.onethingai.com/api/v1/account/wallet/detail"
    headers:
      Authorization: "Bearer 123456"
      Content-Type: "application/json"
    result_template: "网心云: {{data.availableBalance}} 元"
```

当请求```balance```的时候，对应行应返回

```
网心云 0.05 元
```

### 👴使用多请求头

对于一些服务商，可能需要填写额外的Content-Type头

你可以使用```&&```符号分隔多个请求头，就像这样：

```
Authorization: xxx && Content-Type: yyy
```

如果Content-Type以application/json填写到配置里，就会像这样

```
网心云|https://api-lab.onethingai.com/api/v1/account/wallet/detail|Authorization: Bearer 123456 && Content-Type: application/json|data.availableBalance|元
```

在新版YAML中，直接在headers下添加键值对。

# 🔥异常处理

他会针对每一行返回异常，当调用的时候异常会显示在消息中（不会泄露token）

| 注解 | 返回的消息 |
| ---- | ---- |
| 当字段数缺失的时候 | 配置格式错误（字段数不正确） |
| 返回的状态码非200 | 服务商名字 请求失败 |
| 获取的值为空/路径找不到 | 服务商名字 未找到字段 配置的字段名 |
| 请求超时 | 服务商名字 请求超时 |
| 任何未定义的异常 | 服务商名字 异常 |

# 🐓注意

- 请求方式默认 GET
- 新版配置需要安装 pyyaml 库：`pip install pyyaml`

# 🩷特别感谢

编写&修改：ChatGPT MiniMax M2.5
修改：Xbodwf
