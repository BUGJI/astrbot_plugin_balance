import aiohttp
import asyncio
import yaml
import re

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig


@register("balance_checker", "BUGJI", "通用查询各种 API 的余额", "v0.2.0")
class BalancePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        self.title = self.config.get("title", "余额查询结果：")
        self.token_config = self.config.get("token_config", "")
        self.services_config = self.config.get("services_config", "")
        self.use_yaml_config: bool = self.config.get("use_yaml_config", False)
        self.enable_llm_tool: bool = self.config.get("enable_llm_tool", False)

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
            return await self._query_yaml()
        
        if not self.token_config.strip():
            return ["未配置 token_config"]

        self._ensure_session()

        lines = self.token_config.strip().splitlines()
        tasks = [self._handle_line(line) for line in lines]

        results = [self.title]

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for r in responses:
            if isinstance(r, str):
                results.append(r)

        return results

    async def _query_yaml(self) -> list[str]:
        if not self.services_config.strip():
            return ["未配置 services_config"]

        try:
            config_data = yaml.safe_load(self.services_config)
            services = config_data.get("services", {})
        except Exception as e:
            logger.error(f"解析 YAML 配置失败: {e}")
            return ["YAML 配置解析失败"]

        if not services:
            return ["未配置任何服务"]

        self._ensure_session()
        
        tasks = []
        for service_name, service_info in services.items():
            tasks.append(self._handle_yaml_service(service_name, service_info))

        results = []
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for r in responses:
            if isinstance(r, str):
                results.append(r)
            elif isinstance(r, Exception):
                logger.error(f"处理 YAML 服务异常: {r}")

        return results

    async def _handle_yaml_service(self, name: str, info: dict) -> str:
        try:
            display_name = info.get("display_name", name)
            url = info.get("url")
            method = info.get("method", "GET").upper()
            headers = info.get("headers", {})
            result_template = info.get("result_template", "{data}")

            if not url:
                return f"{display_name}: 缺失 URL"

            async with self.session.request(method, url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"[{display_name}] HTTP {resp.status}")
                    return f"{display_name}: 请求失败 (HTTP {resp.status})"

                data = await resp.json()
                
                # 渲染模板
                result = result_template
                placeholders = re.findall(r"\{(.*?)\}", result_template)
                
                for path in placeholders:
                    value = self._get_by_path(data, path)
                    if value is None:
                        value = "N/A"
                    result = result.replace(f"{{{path}}}", str(value))
                
                return f"{display_name}:\n{result}"

        except asyncio.TimeoutError:
            return f"{display_name}: 请求超时"
        except Exception as e:
            logger.error(f"[{name}] 处理失败: {type(e).__name__}: {e}")
            return f"{display_name}: 异常"

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