import aiohttp
import asyncio
import yaml
import re
import math
from typing import Any

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig


@register("balance_checker", "BUGJI", "通用查询各种 API 的余额", "v0.3.1")
class BalancePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        self.result_template = self.config.get("result_template", "余额查询结果：\n{result}")
        self.config_content = self.config.get("config_content", "")
        self.config_mode: str = self.config.get("config_mode", "yaml")  # "simple" | "yaml"
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
        output = self.result_template.replace("{result}", "\n".join(results))
        yield event.plain_result(output)

    @filter.llm_tool(name="query_balance")
    async def query_balance(self, event: AstrMessageEvent) -> MessageEventResult:
        """
        查询并返回当前配置的所有余额信息
        """
        if not self.enable_llm_tool:
            yield event.plain_result("余额查询 LLM 工具未启用")
            return

        results = await self._query_all()
        output = self.result_template.replace("{result}", "\n".join(results))
        yield event.plain_result(output)

    async def _query_all(self) -> list[str]:
        if not self.config_content.strip():
            return ["未配置 config_content"]

        if self.config_mode == "yaml":
            return await self._query_yaml()
        
        # simple 模式（兼容旧版格式）
        return await self._query_simple()

    async def _query_yaml(self) -> list[str]:
        if not self.config_content.strip():
            return ["未配置 config_content"]

        try:
            config_data = yaml.safe_load(self.config_content)
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

    async def _query_simple(self) -> list[str]:
        """简单模式：使用旧版格式的配置"""
        self._ensure_session()

        lines = self.config_content.strip().splitlines()
        tasks = [self._handle_line(line) for line in lines]

        results = [self.title]

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for r in responses:
            if isinstance(r, str):
                results.append(r)

        return results

    async def _handle_yaml_service(self, name: str, info: dict) -> str:
        try:
            display_name = info.get("display_name")
            url = info.get("url")
            method = info.get("method", "GET").upper()
            headers = info.get("headers", {})
            result_template = info.get("result_template", "{data}")

            if not url:
                return f"{name}: 缺失 URL" if not display_name else f"{display_name}: 缺失 URL"

            async with self.session.request(method, url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"[{name}] HTTP {resp.status}")
                    return f"{name}: 请求失败 (HTTP {resp.status})" if not display_name else f"{display_name}: 请求失败 (HTTP {resp.status})"

                data = await resp.json()
                # logger.info(f"[{name}] API 返回: {data}")
                
                # 渲染模板：强制使用双层 {{data.xxx}}
                result = self._render_template(result_template, data)
                
                if display_name:
                    return f"{display_name}:\n{result}"
                return result

        except asyncio.TimeoutError:
            return f"{display_name}: 请求超时"
        except Exception as e:
            logger.error(f"[{name}] 处理失败: {type(e).__name__}: {e}")
            return f"{display_name}: 异常"

    def _render_template(self, template: str, data: dict) -> str:
        """渲染模板，只处理双层大括号 {{...}}，单层大括号 {...} 忽略（除非在双层内部）"""
        result = template
        
        # 查找所有双层大括号 {{...}}，内部可以包含任意字符（包括大括号）
        # 使用非贪婪匹配
        pattern = r'\{\{(.*?)\}\}'
        
        def process_match(match):
            inner_content = match.group(1)  # 获取 {{ }} 内部的内容
            
            # 检查内部是否包含单层大括号 {xxx}
            if re.search(r'\{[^{}]+\}', inner_content):
                # 有内层大括号：先替换内层的 {path} 为实际值
                inner_pattern = r'\{([^{}]+)\}'
                
                def replace_path(m):
                    path = m.group(1)
                    value = self._get_by_path(data, path)
                    
                    if value is None:
                        return "N/A"
                    
                    # 转为字符串用于计算
                    try:
                        if isinstance(value, str):
                            # 提取数字
                            cleaned = re.sub(r'[^\d.-]', '', value)
                            if cleaned:
                                value = float(cleaned) if '.' in cleaned else int(cleaned)
                    except (ValueError, TypeError):
                        pass
                    
                    return str(value)
                
                # 替换所有内层路径
                expr = re.sub(inner_pattern, replace_path, inner_content)
                
                # 计算表达式
                try:
                    computed = self._eval_expr(expr)
                    return str(computed)
                except Exception as e:
                    logger.warning(f"表达式计算失败: {expr}, 错误: {e}")
                    return "N/A"
            else:
                # 没有内层大括号：直接获取路径的值
                value = self._get_by_path(data, inner_content)
                if value is None:
                    return "N/A"
                
                # 格式化输出
                if isinstance(value, (int, float)):
                    if isinstance(value, float) and not value.is_integer():
                        return f"{value:.2f}"
                return str(value)
        
        # 替换所有双层大括号
        result = re.sub(pattern, process_match, result)
        
        return result

    def _eval_expr(self, expr: str) -> Any:
        """计算数学表达式"""
        try:
            result = expr
            # 处理百分号
            result = result.replace('%', '/100')
            
            # 安全函数
            safe_funcs = {
                'abs': abs, 'round': round, 'min': min, 'max': max,
                'pow': pow, 'sqrt': math.sqrt, 'floor': math.floor,
                'ceil': math.ceil, 'log': math.log, 'log10': math.log10,
                'exp': math.exp, 'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
                'pi': math.pi, 'e': math.e
            }
            
            eval_result = eval(result, {"__builtins__": {}}, safe_funcs)
            
            # 格式化
            if isinstance(eval_result, float):
                if eval_result.is_integer():
                    return int(eval_result)
                return round(eval_result, 2)
            return eval_result
        except Exception as e:
            logger.warning(f"公式计算失败: {expr}, 错误: {e}")
            return "错误"

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