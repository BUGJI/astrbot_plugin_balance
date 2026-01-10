import aiohttp
import asyncio
import yaml
import re

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig


@register("balance_checker", "BUGJI", "通用查询各种 API 的余额，支持YAML配置", "v0.3.0")
class BalancePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        self.title = self.config.get("title", "余额查询结果：")
        self.token_config = self.config.get("token_config", "")
        self.services_config = self.config.get("services_config", "")
        self.enable_llm_tool: bool = self.config.get("enable_llm_tool", False)
        self.use_yaml_config: bool = self.config.get("use_yaml_config", False)

        self.session: aiohttp.ClientSession | None = None

    async def initialize(self):
        # initialize 不再依赖
        logger.info("BalancePlugin initialize called")

    async def terminate(self):
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("BalancePlugin 已卸载")

    def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    @filter.command("balance")
    async def balance(self, event: AstrMessageEvent):
        results = await self._query_all()
        yield event.plain_result("\n".join(results))

    @filter.llm_tool(name="query_balance")
    async def query_balance(self, event: AstrMessageEvent) -> MessageEventResult:
        """
        查询并返回当前配置的所有余额信息
        """
        if not self.enable_llm_tool:
            yield event.plain_result("余额查询 LLM 工具未启用")
            return

        results = await self._query_all()
        yield event.plain_result("\n".join(results))

    async def _query_all(self) -> list[str]:
        if self.use_yaml_config:
            if self.services_config.strip():
                return await self._query_services()
            else:
                return ["未配置YAML服务"]
        else:
            if self.token_config.strip():
                return await self._query_legacy()
            else:
                return ["未配置旧版服务"]

    async def _query_legacy(self) -> list[str]:
        self._ensure_session()

        lines = self.token_config.strip().splitlines()
        tasks = [self._handle_line(line) for line in lines]

        results = [self.title]

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for r in responses:
            if isinstance(r, str):
                results.append(r)

        return results

    async def _query_services(self) -> list[str]:
        try:
            services = yaml.safe_load(self.services_config)
        except Exception as e:
            return [f"YAML配置解析失败: {e}"]

        if not isinstance(services, dict):
            return ["services配置必须是字典"]

        self._ensure_session()

        tasks = []
        for name, service in services.items():
            if not service.get('url'):
                continue  # 跳过没有配置URL的服务
            service_copy = service.copy()
            service_copy['name'] = name
            tasks.append(self._handle_service(service_copy))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for r in responses:
            if isinstance(r, str):
                results.append(r)

        return results

    async def _handle_service(self, service: dict) -> str:
        try:
            display_name = service.get('display_name', service.get('name', 'Unknown'))
            url = service.get('url')
            if not url:
                return f"{display_name} 未配置URL"
            headers = service.get('headers', {})
            result_template = service.get('result_template', '')
            method = service.get('method', 'GET').upper()

            async with self.session.request(method, url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"[{display_name}] HTTP {resp.status}")
                    return f"{display_name} 请求失败"

                data = await resp.json()
                result = self._render_template(result_template, data)
                return f"{display_name}:\n{result}"

        except asyncio.TimeoutError:
            return f"{display_name} 请求超时"
        except Exception as e:
            logger.error(f"[{display_name}] 处理失败: {type(e).__name__}")
            return f"{display_name} 异常"

    def _render_template(self, template: str, data) -> str:
        def replacer(match):
            path = match.group(1)
            value = self._get_by_path(data, path)
            return str(value) if value is not None else "N/A"
        return re.sub(r'\{([^}]+)\}', replacer, template)

    async def _handle_line(self, line: str) -> str:
        try:
            parts = line.split("|")
            if len(parts) != 5:
                return "配置格式错误（字段数不正确）"

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

    def _get_by_path(self, data, path: str):
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
