# 旧版单行配置（Simple 模式）

> ⚠️ 此配置模式已不再推荐，建议使用 YAML 模式（支持内置解析器和模板公式）。
> 保留此文档仅用于存量配置迁移参考。

## 格式

配置项以 `|` 符号分割，一行一个：

```
备注|请求地址|请求头|要读取的字段名|金额单位
```

| 项目 | 用途 |
| ---- | ---- |
| 备注 | 用于显示API服务商名字 |
| 请求地址 | 即显式API地址，通常 http(s) 开头 |
| 请求头 | 即填写密钥头的地址，通常为 `Authorization: Bearer xxxxxx` |
| 要读取的字段名 | 通常余额会返回 json 格式，自动匹配余额字段并且获取余额（支持 `a.b.0.c` 路径） |
| 单位 | 一个自定义后缀，通常写 元、积分 |

## 示例

```
OneThingAI 网心云|https://api-lab.onethingai.com/api/v1/account/wallet/detail|Authorization: Bearer 你的token|data.availableBalance|元
硅基流动|https://api.siliconflow.cn/v1/user/info|Authorization: Bearer 你的token|data.totalBalance|元
Deepseek|https://api.deepseek.com/user/balance|Authorization: Bearer 你的token|balance_infos.0.total_balance|元
百度|https://billing.baidubce.com/v1/finance/cash/balance|Authorization: 你的token|cashBalance|元
```

## 多请求头

使用 `&&` 符号分隔多个请求头：

```
Authorization: Bearer xxx && Content-Type: application/json
```

完整示例：

```
网心云|https://api-lab.onethingai.com/api/v1/account/wallet/detail|Authorization: Bearer 123456 && Content-Type: application/json|data.availableBalance|元
```

## 添加第三方（Simple 模式）

以网心AI为例：

curl 请求：
```bash
curl 'https://api-lab.onethingai.com/api/v1/account/wallet/detail' -H 'Authorization: Bearer {TOKEN}'
```

返回：
```json
{
    "code": 0,
    "msg": "Success",
    "data": {
      "availableBalance": 0.05,
      "availableVoucherCash": 72.93,
      "consumeCashTotal": 6
    }
}
```

token 为 `123456` 时，配置为：

```
网心云|https://api-lab.onethingai.com/api/v1/account/wallet/detail|Authorization: Bearer 123456|data.availableBalance|元
```

查询 `balance` 时返回：

```
网心云 0.05 元
```

## Simple 模式异常信息

| 情况 | 返回的消息 |
| ---- | ---- |
| 字段数不正确 | `配置格式错误（字段数不正确）` |
| 状态码非 200 | `服务商名字 请求失败` |
| 值为空/路径找不到 | `服务商名字 未找到字段 配置的字段名` |
| 请求超时 | `服务商名字 请求超时` |
| 其他异常 | `服务商名字 异常` |
