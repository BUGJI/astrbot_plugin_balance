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


# 内置解析器预设：type 字段对应此表，用户只需提供 api_key
_BUILTIN_PARSERS = {
    "deepseek": {
        "url": "https://api.deepseek.com/user/balance",
        "headers": {
            "Accept": "application/json",
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "DeepSeek: {{balance_infos.0.total_balance}} 元",
    },
    "siliconflow": {
        "url": "https://api.siliconflow.cn/v1/user/info",
        "headers": {
            "Authorization": "Bearer {api_key}",
            "Content-Type": "application/json",
        },
        "result_template": "硅基流动: {{data.totalBalance}} 元",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/credits",
        "headers": {
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "OpenRouter: ${{data.total_credits}}",
    },
    "oneapi": {
        # One-API / New-API 自建实例，需要 base_url（如 https://your.domain）
        "url": "{base_url}/api/user/self",
        "headers": {
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "{{data.email}}: {{data.balance}} 元",
    },
    "moonshot": {
        "url": "https://api.moonshot.cn/v1/users/me/balance",
        "headers": {
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "月之暗面: {{data.available_balance}} 元",
    },
    "openai": {
        "url": "https://api.openai.com/v1/dashboard/billing/subscription",
        "headers": {
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "OpenAI: ${{hard_limit_usd}}",
    },
    "onething": {
        "url": "https://api-lab.onethingai.com/api/v1/account/wallet/detail",
        "headers": {
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "OneThing: {{data.availableBalance}} 元",
    },
    "minimax": {
        "url": "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains",
        "headers": {
            "Authorization": "Bearer {api_key}",
            "Content-Type": "application/json",
        },
        "result_template": "MiniMax: 剩余 {{round({model_remains.0.current_interval_total_count}-{model_remains.0.current_interval_usage_count})}}/{{model_remains.0.current_interval_total_count}} ({{round(({model_remains.0.current_interval_total_count}-{model_remains.0.current_interval_usage_count})/{model_remains.0.current_interval_total_count}*100, 1)}}%), 本周 {{round({model_remains.0.current_weekly_total_count}-{model_remains.0.current_weekly_usage_count})}}/{{model_remains.0.current_weekly_total_count}}",
    },
    "kimi": {
        "url": "https://api.moonshot.cn/v1/users/me/balance",
        "headers": {
            "Accept": "application/json",
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "Kimi: {{data.available_balance}} 元",
    },
    "kimi-full": {
        "url": "https://api.moonshot.cn/v1/users/me/balance",
        "headers": {
            "Accept": "application/json",
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "Kimi: {{data.available_balance}} 元 (现金: {{data.cash_balance}} 元, 代金券: {{data.voucher_balance}} 元)",
    },
    "aihubmix": {
        "url": "https://aihubmix.com/api/user/self", 
        "headers": {
            "Accept": "application/json",
            "Authorization": "Bearer {api_key}",  # 使用 Manage Key
        },
        # 计算公式：余额 = quota / 500000，保留2位小数
        "result_template": "AIHubMix: {{round({data.quota}/500000*7.1, 2)}} 元",
    },
    "apimart": {
        "url": "https://aishuch.com/v1/user/balance",
        "headers": {
            "Accept": "application/json",
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "APIMart: {{round({remain_balance}*7, 2) - round({used_balance}*7, 2)}} 元",
    },
    "apimart-full": {
        "url": "https://aishuch.com/v1/user/balance",
        "headers": {
            "Accept": "application/json",
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "APIMart: {{round({remain_balance}*7, 2)}} 元 (已用: {{round({used_balance}*7, 2)}} 元)",
    },
    "apimart-credits": {
        "url": "https://aishuch.com/v1/user/balance",
        "headers": {
            "Accept": "application/json",
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "APIMart: {{round({remain_credits}, 2) - round({used_credits}, 2)}} 积分",
    },
    "apimart-credits-full": {
        "url": "https://aishuch.com/v1/user/balance",
        "headers": {
            "Accept": "application/json",
            "Authorization": "Bearer {api_key}",
        },
        "result_template": "APIMart: {{round({remain_credits}, 2)}} 积分 (已用: {{round({used_credits}, 2)}} 积分)",
    },
}


@register("balance_checker", "BUGJI", "通用查询各种 API 的余额", "v1.2.1")
class BalancePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        self.result_template = self.config.get("result_template", "余额查询结果：\n{result}")
        self.config_content = self.config.get("config_content", "")
        self.config_mode: str = self.config.get("config_mode", "yaml")  # "simple" | "yaml" | "template_list"
        self.config_templates: list = self.config.get("config", [])
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
            yield event.plain_result("什么都木有~")
            return

        results = await self._query_all()
        output = self.result_template.replace("{result}", "\n".join(results))
        yield event.plain_result(output)

    async def _query_all(self) -> list[str]:
        if self.config_mode == "template_list":
            return await self._query_template_list()

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

    async def _query_template_list(self) -> list[str]:
        """template_list 模式：从结构化配置生成服务列表并查询

        配置格式为 list，每项包含 __template_key 标识模板类型:
          [{"__template_key": "deepseek", "api_key": "sk-xxx", "enable": true}, ...]
        """
        templates = self.config_templates
        if not templates:
            return ["未配置任何模板"]

        # 模板键名 → 内置解析器类型名 的映射
        type_map = {
            "deepseek": "deepseek",
            "siliconflow": "siliconflow",
            "OneThing": "onething",
        }

        services = {}
        for item in templates:
            template_key = item.get("__template_key", "")
            if not item.get("enable", True):
                continue

            if template_key == "Custom":
                request_template = item.get("request_template", "")
                if not request_template or not request_template.strip():
                    continue
                try:
                    custom_services = yaml.safe_load(request_template)
                    if isinstance(custom_services, dict):
                        services.update(custom_services)
                except Exception as e:
                    logger.error(f"解析 Custom 模板失败: {e}")
            else:
                api_key = item.get("api_key", "")
                if not api_key:
                    continue
                parser_type = type_map.get(template_key, template_key.lower())
                services[template_key] = {
                    "type": parser_type,
                    "api_key": api_key,
                }

        if not services:
            return ["未启用任何服务或缺少 API Key"]

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
                logger.error(f"处理模板服务异常: {r}")

        return results

    async def _query_simple(self) -> list[str]:
        """简单模式：使用旧版格式的配置"""
        self._ensure_session()

        lines = self.config_content.strip().splitlines()
        tasks = [self._handle_line(line) for line in lines]

        results = ["余额查询结果："]

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for r in responses:
            if isinstance(r, str):
                results.append(r)

        return results

    async def _handle_yaml_service(self, name: str, info: dict) -> str:
        try:
            # === type 字段判断：内置解析器 vs 自定义 ===
            parser_type = info.get("type", "custom") or "custom"
            display_name = info.get("display_name")

            if parser_type == "custom":
                # 自定义模式：完全由用户提供 url / headers / result_template
                url = info.get("url")
                method = info.get("method", "GET").upper()
                headers = info.get("headers", {})
                result_template = info.get("result_template", "{data}")

                if not url:
                    label = display_name or name
                    return f"{label}: 缺失 URL"

            elif parser_type in _BUILTIN_PARSERS:
                # 内置解析器模式：预设填充，用户只需 api_key
                preset = dict(_BUILTIN_PARSERS[parser_type])

                display_name = display_name or preset.get("display_name", name)

                api_key = info.get("api_key", "")
                base_url = info.get("base_url", "")

                # 必需字段校验
                if not api_key:
                    return f"{display_name}: 缺少 api_key"
                preset_url = preset.get("url", "")
                if "{base_url}" in preset_url and not base_url:
                    return f"{display_name}: 缺少 base_url（该类型需要自建实例地址）"

                # URL：用户可覆盖预设
                url = info.get("url") or preset_url
                url = url.replace("{base_url}", base_url)

                # Headers：预设 + 用户可追加/覆盖
                headers = {}
                for k, v in preset.get("headers", {}).items():
                    headers[k] = v.replace("{api_key}", api_key).replace("{base_url}", base_url)
                for k, v in info.get("headers", {}).items():
                    headers[k] = v.replace("{api_key}", api_key).replace("{base_url}", base_url)

                # Template & Method：用户可覆盖预设
                result_template = info.get("result_template") or preset.get("result_template", "{data}")
                method = info.get("method", preset.get("method", "GET")).upper()

            else:
                # 未知的内置类型
                label = display_name or name
                return f"{label}: 未知的内置解析器类型 '{parser_type}'，可选: {', '.join(sorted(_BUILTIN_PARSERS.keys()))}"

            # === 统一的请求 & 渲染逻辑 ===
            async with self.session.request(method, url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"[{name}] HTTP {resp.status} {url}")
                    label = display_name or name
                    return f"{label}: 请求失败 (HTTP {resp.status})"

                data = await resp.json()
                # logger.info(f"[{name}] API 返回: {data}")

                result = self._render_template(result_template, data)
                logger.debug(f"[{name}] 结果: {result}")
                return result

        except asyncio.TimeoutError:
            label = display_name or name
            return f"{label}: 请求超时"
        except Exception as e:
            logger.error(f"[{name}] 处理失败: {type(e).__name__}: {e}")
            label = display_name or name
            return f"{label}: 异常"

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
