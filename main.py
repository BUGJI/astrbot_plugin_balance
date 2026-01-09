import aiohttp
import asyncio

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig


@register("balance_checker", "BUGJI", "通用查询各种 API 的余额", "v0.1.0")
class BalancePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.title = self.config.get("title", "余额查询结果：")
        self.token_config = self.config.get("token_config", "")
        self.session: aiohttp.ClientSession | None = None

    async def initialize(self):
        self.session = aiohttp.ClientSession()
        logger.info("BalancePlugin 初始化完成")

    async def terminate(self):
        if self.session:
            await self.session.close()
        logger.info("BalancePlugin 已卸载")

    @filter.command("balance")
    async def balance(self, event: AstrMessageEvent):
        if not self.token_config.strip():
            yield event.plain_result("未配置 token_config")
            return

        lines = self.token_config.strip().splitlines()
        tasks = [self._handle_line(line) for line in lines]

        results = [self.title]

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for r in responses:
            if isinstance(r, str):
                results.append(r)

        yield event.plain_result("\n".join(results))

    async def _handle_line(self, line: str) -> str:
        try:
            parts = line.split("|")
            if len(parts) != 5:
                return "配置格式错误（需要 5 段）"

            remark, url, header_str, json_path, unit = parts

            headers = self._parse_headers(header_str)

            async with self.session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"[{remark}] HTTP {resp.status}")
                    return f"{remark} 请求失败"

                data = await resp.json()
                value = self._get_by_path(data, json_path)

                if value is None:
                    return f"{remark} 未找到字段 {json_path}"

                return f"{remark} {value} {unit}"

        except asyncio.TimeoutError:
            return f"{remark} 请求超时"
        except Exception as e:
            logger.error(f"[{remark}] 处理失败: {type(e).__name__}")
            return f"{remark} 异常"

    def _parse_headers(self, header_str: str) -> dict:
        headers = {}
        for item in header_str.split("&&"):
            if ":" not in item:
                continue
            k, v = item.split(":", 1)
            headers[k.strip()] = v.strip()
        return headers

    def _get_by_path(self, data: dict, path: str):
        """
        支持 data.xxx.yyy / xxx / data.list.0.value
        """
        current = data
        for part in path.split("."):
            if isinstance(current, list):
                try:
                    current = current[int(part)]
                except Exception:
                    return None
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current
