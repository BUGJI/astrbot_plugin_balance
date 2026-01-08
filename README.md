# 💴万能余额查询

AstrBot 万能余额查询，只需要详细填写配置文件即可

优势：
- 支持90%的余额请求格式
- 配置中任意一行失败，不影响其他行

# 👉快速开始

配置项以```|```分割，一行一个，格式如下：

```备注|请求地址|请求头|要读取的字段名|单位```

| 项目 | 用途 |
| ---- | ---- |
| 备注 | 用于显示API服务商名字 |
| 请求地址 | 即显式API地址，通常http(s)开头 |
| 请求头 | 即填写密钥头的地址，通常为Authorization: Bearer xxxxxx |
| 要读取的字段名 | 通常余额会返回json格式，自动匹配余额字段并且获取余额 |
| 单位 | 一个自定义后缀，通常写 元、积分 |

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
    "data": {
      "availableBalance": 0.05,       #假设这一项是余额
      "availableVoucherCash": 72.93,  
      "consumeCashTotal": 6,          
    }
}
```

那么应将配置写为：
```text
网心云|https://api-lab.onethingai.com/api/v1/account/wallet/detail|Authorization: Bearer 123456|availableBalance|元
```
当请求```/balance```的时候，就会返回
```
余额查询结果：
网心云 0.05 元
```

# 🔴注意

- 请求方式默认 GET
- 请求头目前只支持一条（但是 90% 场景够用）

# 🩷特别感谢

编写：ChatGPT
