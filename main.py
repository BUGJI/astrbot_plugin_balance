import aiohttp
import asyncio

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


@register("balance_checker", "BUGJI", "通用查询各种API的余额", "1.0.0")
class BalancePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config = context.config
        # token_config 是一个多行字符串
        self.token_config = self.config.get("token_config", "")

    async def initialize(self):
        logger.info("BalancePlugin 初始化完成")

    @filter.command("balance")
    async def balance(self, event: AstrMessageEvent):
        results = []

        if not self.token_config.strip():
            yield event.plain_result("未配置 token_config")
            return

        lines = self.token_config.strip().splitlines()

        async with aiohttp.ClientSession() as session:
            for line in lines:
                try:
                    remark, url, header_str, json_key, unit = line.split("|", 4)

                    # 解析 Header
                    header_name, header_value = header_str.split(":", 1)
                    headers = {
                        header_name.strip(): header_value.strip()
                    }

                    async with session.get(url, headers=headers, timeout=10) as resp:
                        if resp.status != 200:
                            logger.warning(f"{remark} 请求失败 HTTP {resp.status}")
                            results.append(f"{remark} 请求失败")
                            continue

                        data = await resp.json()

                        # 默认从 data 节中取值
                        value = data.get("data", {}).get(json_key, None)
                        if value is None:
                            results.append(f"{remark} 未找到字段 {json_key}")
                        else:
                            results.append(f"{remark} {value} {unit}")

                except Exception as e:
                    logger.exception(f"处理配置行失败: {line}")
                    results.append(f"{line.split('|', 1)[0]} 异常")

        if results:
            yield event.plain_result("\n".join(results))
        else:
            yield event.plain_result("无可用结果")

    async def terminate(self):
        logger.info("BalancePlugin 已卸载")
