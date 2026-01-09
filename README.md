# 💴万能余额查询

AstrBot 万能余额查询，只需要详细填写配置文件即可

优势：
- 支持99%的余额请求格式
- 配置中任意一行失败，不影响其他行
- 支持LLM请求（可开关）

# 👉快速开始

使用```balance```命令，则会返回如下格式的消息：
```
余额查询结果：
A云 1.14 元
B云 5.14 元
```

## 📕模板配置

你可以直接粘贴至配置文件，只需要替换您账户的有效token即可

网心AI：

```
网心云|https://api-lab.onethingai.com/api/v1/account/wallet/detail|Authorization: Bearer 你的token|data.availableBalance|元
```

硅基流动：
```
哈基流动|https://api.siliconflow.cn/v1/user/info|Authorization: Bearer 你的token|data.totalBalance|元
```

Deepseek：
```
蓝色鲸鱼|https://api.deepseek.com/user/balance|Authorization: Bearer 你的token|data.total_balance|元
```

百度：
```
文档这么写的但是我没调用成功|https://billing.baidubce.com/v1/finance/cash/balance|Authorization: 你的token|cashBalance|元
```

## 🔍解读配置

配置项以```|```符号分割，一行一个，格式如下：

```备注|请求地址|请求头|要读取的字段名|金额单位```

| 项目 | 用途 |
| ---- | ---- |
| 备注 | 用于显示API服务商名字 |
| 请求地址 | 即显式API地址，通常http(s)开头 |
| 请求头 | 即填写密钥头的地址，通常为Authorization: Bearer xxxxxx |
| 要读取的字段名 | 通常余额会返回json格式，自动匹配余额字段并且获取余额 |
| 单位 | 一个自定义后缀，通常写 元、积分 |

# 💩通用配置

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
当请求```balance```的时候，就会返回
```
余额查询结果：
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

# 🐓注意

- 请求方式默认 GET

# 🩷特别感谢

编写&修改：ChatGPT
