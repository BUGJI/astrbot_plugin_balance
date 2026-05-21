# 💴万能余额查询

  <img src="./logo.png" width="280" height="280" align="right"/>

AstrBot 万能余额查询，只需要填写配置文件即可

优势：
- 支持99%的余额请求格式
- 内置解析器：常用服务开箱即用，只需填 api_key
- 配置中任意一行失败，不影响其他行
- 支持LLM请求（可开关）
- 简易配置，支持YAML接入任何源，支持URL参数、复杂Header、多结果展示

# 👉快速开始

使用```balance```命令，则会返回如下格式的消息：
```
余额查询结果：
A云 1.14 元
B云 5.14 元
```

## 📕模板配置

如没有特殊站点，下面内置解析器的版本足够大部分人使用

可以直接复制并修改 `api_key` 字段为你的 token

### 🚀 内置解析器

只需填写 `api_key` 即可

我们内置的列表：

| 服务商 | 支持程度 |
| -------- | -- |
| Deepseek | ✅ |
| Siliconflow | ✅ |
| Onething | ✅ |
| NewAPI | 计划中 |
| Baidu | 计划中 |
| Custom | 自定义 |

如没有支持的站点 请跳转到下方 自定义格式

默认样式不一定会让大伙喜欢，如果感觉返回值可以简化，以及如果有新的API可以固化进来，可以开一个issues

### 自定义格式

对于没有支持的站点，或者想自定义格式，可以填写自定义模板配置查询输出

```yaml

Deepseek:
  url: "https://api.deepseek.com/user/balance"
  method: "GET"
  headers:
    Accept: "application/json"
    Authorization: "Bearer Your-APIKEY" # API-KEY 填写位置
  result_template: "Deepseek: {{balance_infos.0.total_balance}} 元" # 返回模板，双层括号为json节

SiliconFlow:
  url: "https://api.siliconflow.cn/v1/user/info"
  method: "GET"
  headers:
    Authorization: "Bearer Your-APIKEY"
    Content-Type: "application/json"
  result_template: "哈基流动: {{data.totalBalance}} CNY/元/人民币/Q币" # 模板可以修改成任何东西

new-api:  # 此处为基于NewApi站点的通用配置，可以改成对应站点名字
  url: "http://newapi.domain/api/user/self" # 替换newapi.domain为你的站点地址
  method: "GET"
  headers:
    Authorization: "Bearer Your-Access-Token" # 不是APIKEY，需要登录 new-api 后台 → 个人设置 → 生成访问令牌（Access Token）
    New-Api-User: "1" # 用户ID
  result_template: "new-api: {{round({data.quota}/500000, 2)}} 美元 (已用 {{round({data.used_quota}/500000, 2)}})"
```

### 解读配置

| 项目 | 用途 |
| ---- | ---- |
| typ**e** | 代表字段类型，用于判断是使用已有的模板，还是使用自定义模板 |
| url | 请求地址，支持URL参数 |
| headers | 请求头，键值对形式，支持特殊字符 |
| method | 请求方法（可选，默认GET） |
| result_template | 结果模板，使用 `{{path}}` 替换，支持公式计算 |

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

```yaml
OneThing:
  url: "https://api-lab.onethingai.com/api/v1/account/wallet/detail" # 请求地址
  method: "GET"
  headers:
    Authorization: "Bearer 123456" # 余额
    Content-Type: "application/json"
  result_template: "网心云: {{data.availableBalance}} 元" # 配置节
```

当请求```balance```的时候，对应行应返回

```
网心云 0.05 元
```

### 模板高级语法（通常用于精确计算）

通常用于特殊站点，你可以给常见站点配置，如计算百分比用量

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

# 🔥异常处理

他会针对每一行返回异常，当调用的时候异常会显示在消息中（不会泄露token）

| 注解 | 返回的消息 |
| ---- | ---- |
| 当字段数缺失的时候 | 配置格式错误（字段数不正确） |
| 返回的状态码非200 | 服务商名字 请求失败 |
| 获取的值为空/路径找不到 | 服务商名字 未找到字段 配置的字段名 |
| 请求超时 | 服务商名字 请求超时 |
| 任何未定义的异常 | 服务商名字 异常 |

> [更早期的配置](https://github.com/BUGJI/astrbot_plugin_balance/blob/dev/SIMPLE_CONFIG.MD)

# 🩷特别感谢

修改：
- Xbodwf

修改 (AI)：
- ChatGPT
- MiniMax M2.5
- Deepseek V4 Pro
- Qwen Coder
