import re
import ipaddress
import socket
from typing import Dict, Any, List
from urllib.parse import urlparse


class NetworkSecurityController:
    """网络安全控制器"""

    def __init__(self, components: Dict[str, Any] = None):
        self.components = components
        self._i18n_manager = self.components.get("i18n_manager")

        self.config_manager = self.components.get("config_manager")
        self.security_config = self.config_manager.get_security_config()
        self.network_config = self.security_config.get("network", {})

        # 基础配置
        self.max_requests_per_minute = self.network_config.get("max_requests_per_minute", 60)
        self.max_concurrent_connections = self.network_config.get("max_concurrent_connections", 10)
        self.request_timeout = self.network_config.get("request_timeout", 30)
        self.allowed_protocols = self.network_config.get("allowed_protocols", ["http", "https"])
        self.allowed_ports = self.network_config.get("allowed_ports", [80, 443, 8080, 8443])
        self.blocked_ports = self.network_config.get("blocked_ports", [22, 23, 3389, 5432, 3306])

        # 域名控制
        self.domain_whitelist = self.network_config.get("domain_whitelist", [])
        self.domain_blacklist = self.network_config.get("domain_blacklist", [])
        self.enable_domain_filtering = self.network_config.get("enable_domain_filtering", True)

        # 任务类型特定配置
        self.task_specific_config = self.network_config.get("task_specific", {})

        # 私有IP地址范围
        self.blocked_ip_ranges = [
            ipaddress.ip_network("127.0.0.0/8"),
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
            ipaddress.ip_network("169.254.0.0/16"),
        ]

    def validate_network_access(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """网络访问验证 - 集成新的策略架构"""
        task_type = context.get("task_type", "general")

        # 获取网络策略配置
        if self.config_manager:
            network_config = self.config_manager.get_cache_validation_network_config(task_type)
            policy_level = network_config.get("policy_level", "filtered")

            # 根据策略级别进行验证
            if policy_level == "unrestricted":
                unrestricted_message = self._i18n_manager.t("network.validation_disabled")
                return {"allowed": True, "reason": unrestricted_message}
            elif policy_level == "strict":
                strict_message = self._i18n_manager.t("network.strict_mode_blocks_all")
                return {"allowed": False, "reason": strict_message}
            elif policy_level == "filtered":
                return self._validate_domain_filtering(code, network_config, task_type)
            else:  # open
                open_message = self._i18n_manager.t("network.open_mode_allows_all")
                return {"allowed": True, "reason": open_message}

        # 回退到原有逻辑
        default_allow_message = self._i18n_manager.t("network.default_allow")
        return {"allowed": True, "reason": default_allow_message}

    def _validate_domain_filtering(
        self, code: str, network_config: Dict[str, Any], task_type: str
    ) -> Dict[str, Any]:
        """验证域名过滤"""
        if not network_config.get("domain_filtering_enabled", True):
            filtering_disabled_message = self._i18n_manager.t("network.domain_filtering_disabled")
            return {"allowed": True, "reason": filtering_disabled_message}

        # 从代码中提取域名
        accessed_domains = self._extract_domains_from_code(code)

        whitelist = network_config.get("domain_whitelist", [])
        blacklist = network_config.get("domain_blacklist", [])

        for domain in accessed_domains:
            if any(domain.endswith(blocked) for blocked in blacklist):
                blacklist_message = self._i18n_manager.t(
                    "network.domain_in_blacklist", domain=domain
                )
                return {"allowed": False, "reason": blacklist_message}

            if not any(domain.endswith(allowed) for allowed in whitelist):
                not_in_whitelist_message = self._i18n_manager.t(
                    "network.domain_not_in_whitelist", domain=domain
                )
                return {"allowed": False, "reason": not_in_whitelist_message}

        validation_passed_message = self._i18n_manager.t("network.domain_validation_passed")
        return {"allowed": True, "reason": validation_passed_message}

    def _extract_domains_from_code(self, code: str) -> list:
        """从代码中提取域名访问"""
        import re

        domain_pattern = r'https?://([^/\s"\']+)'
        domains = re.findall(domain_pattern, code)

        bare_domain_pattern = r'["\']([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']'
        bare_domains = re.findall(bare_domain_pattern, code)

        all_domains = list(set(domains + bare_domains))

        filtered_domains = []
        for domain in all_domains:
            if "." in domain and len(domain.split(".")) >= 2:
                if not re.match(r"^\d+\.\d+\.\d+\.\d+$", domain):
                    filtered_domains.append(domain)

        return filtered_domains

    def analyze_network_risk(
        self, code: str, parameters: Dict[str, Any], task_type: str = None
    ) -> Dict[str, Any]:
        """完整的网络风险分析"""
        # 根据任务类型调整安全策略
        effective_config = self._get_effective_config_for_task(task_type)

        risk_analysis = {
            "risk_level": "low",
            "network_operations": [],
            "blocked_operations": [],
            "suspicious_patterns": [],
            "url_validation": self._validate_urls(parameters, effective_config),
            "requires_network_permission": False,
            "task_type": task_type,
            "effective_config": effective_config,
        }

        # 检测网络相关模式
        network_patterns = self._detect_network_patterns(code)
        if network_patterns:
            risk_analysis["network_operations"] = network_patterns
            risk_analysis["requires_network_permission"] = True
            risk_analysis["risk_level"] = "medium"

        # 检查URL访问权限
        if risk_analysis["url_validation"]["blocked_urls"]:
            risk_analysis["risk_level"] = "high"
            risk_analysis["blocked_operations"].extend(
                risk_analysis["url_validation"]["blocked_urls"]
            )

        # 检测可疑模式
        suspicious_patterns = self._detect_suspicious_patterns(code)
        if suspicious_patterns:
            risk_analysis["suspicious_patterns"] = suspicious_patterns
            risk_analysis["risk_level"] = "high"

        return risk_analysis

    def _get_effective_config_for_task(self, task_type: str) -> Dict[str, Any]:
        """根据任务类型获取有效的网络配置"""
        base_config = {
            "enable_domain_filtering": self.enable_domain_filtering,
            "domain_whitelist": self.domain_whitelist.copy(),
            "domain_blacklist": self.domain_blacklist.copy(),
            "allowed_protocols": self.allowed_protocols.copy(),
            "allowed_ports": self.allowed_ports.copy(),
            "blocked_ports": self.blocked_ports.copy(),
        }

        # 搜索任务的特殊处理
        if task_type == "data_fetch":
            search_config = self.task_specific_config.get("data_fetch", {})

            # 搜索任务可以禁用域名过滤或使用扩展白名单
            if search_config.get("disable_domain_filtering", False):
                base_config["enable_domain_filtering"] = False
            elif search_config.get("extended_domain_whitelist"):
                base_config["domain_whitelist"].extend(search_config["extended_domain_whitelist"])

            # 搜索任务可能需要更多端口
            if search_config.get("additional_allowed_ports"):
                base_config["allowed_ports"].extend(search_config["additional_allowed_ports"])

        return base_config

    def _detect_network_patterns(self, code: str) -> List[str]:
        """检测网络相关模式"""
        network_patterns = [
            r"requests\.",
            r"urllib\.",
            r"http\.client",
            r"socket\.",
            r"telnetlib\.",
            r"ftplib\.",
            r"smtplib\.",
            r"poplib\.",
            r"imaplib\.",
            r"httpx\.",
            r"aiohttp\.",
        ]

        detected = []
        for pattern in network_patterns:
            if re.search(pattern, code):
                detected.append(pattern)

        return detected

    def _detect_suspicious_patterns(self, code: str) -> List[str]:
        """检测可疑网络模式"""
        suspicious_patterns = [
            r"socket\.socket\(",
            r"socket\.create_connection\(",
            r"subprocess\..*curl",
            r"subprocess\..*wget",
            r"os\.system.*curl",
            r"os\.system.*wget",
            r"eval\(.*http",
            r"exec\(.*http",
        ]

        detected = []
        for pattern in suspicious_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                detected.append(pattern)

        return detected

    def _validate_urls(
        self, parameters: Dict[str, Any], effective_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用有效配置验证URL访问权限"""
        validation_result = {"valid_urls": [], "blocked_urls": [], "invalid_urls": []}

        urls = self._extract_urls(parameters)

        for url in urls:
            try:
                parsed = urlparse(url)

                # 协议检查
                if parsed.scheme not in effective_config["allowed_protocols"]:
                    validation_result["blocked_urls"].append(
                        f"Blocked protocol {parsed.scheme}: {url}"
                    )
                    continue

                # 端口检查
                port = parsed.port or (80 if parsed.scheme == "http" else 443)
                if port in effective_config["blocked_ports"]:
                    validation_result["blocked_urls"].append(f"Blocked port {port}: {url}")
                    continue

                if (
                    effective_config["allowed_ports"]
                    and port not in effective_config["allowed_ports"]
                ):
                    validation_result["blocked_urls"].append(
                        f"Port {port} not in allowed list: {url}"
                    )
                    continue

                # 域名检查（使用有效配置）
                if effective_config["enable_domain_filtering"]:
                    domain_check = self._validate_domain_with_config(
                        parsed.hostname, effective_config
                    )
                    if not domain_check["allowed"]:
                        validation_result["blocked_urls"].append(
                            f"Domain blocked: {url} - {domain_check['reason']}"
                        )
                        continue

                # IP地址检查
                ip_check = self._validate_ip_access(parsed.hostname)
                if not ip_check["allowed"]:
                    validation_result["blocked_urls"].append(
                        f"IP access blocked: {url} - {ip_check['reason']}"
                    )
                    continue

                validation_result["valid_urls"].append(url)

            except Exception as e:
                validation_result["invalid_urls"].append(f"Invalid URL {url}: {str(e)}")

        return validation_result

    def _validate_domain_with_config(
        self, hostname: str, effective_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用有效配置验证域名访问权限"""
        if not hostname:
            empty_hostname_message = self._i18n_manager.t("network.empty_hostname")
            return {"allowed": False, "reason": empty_hostname_message}

        # 黑名单检查
        for blocked_domain in effective_config["domain_blacklist"]:
            if hostname.endswith(blocked_domain):
                domain_blacklisted_message = self._i18n_manager.t(
                    "network.domain_blacklisted", domain=blocked_domain
                )
                return {"allowed": False, "reason": domain_blacklisted_message}

        # 白名单检查
        if effective_config["domain_whitelist"]:
            for allowed_domain in effective_config["domain_whitelist"]:
                if hostname.endswith(allowed_domain):
                    domain_whitelisted_message = self._i18n_manager.t(
                        "network.domain_whitelisted", domain=allowed_domain
                    )
                    return {"allowed": True, "reason": domain_whitelisted_message}
            domain_not_whitelisted_message = self._i18n_manager.t("network.domain_not_whitelisted")
            return {"allowed": False, "reason": domain_not_whitelisted_message}

        no_restrictions_message = self._i18n_manager.t("network.no_domain_restrictions")
        return {"allowed": True, "reason": no_restrictions_message}

    def _extract_urls(self, parameters: Dict[str, Any]) -> List[str]:
        """从参数中提取URL"""
        urls = []
        url_keys = ["url", "base_url", "endpoint", "api_url", "target_url", "source_url"]

        for key in url_keys:
            if key in parameters:
                param_info = parameters[key]
                if isinstance(param_info, dict) and "value" in param_info:
                    url_value = param_info["value"]
                else:
                    url_value = param_info

                if isinstance(url_value, str) and url_value.startswith(("http://", "https://")):
                    urls.append(url_value)
                elif isinstance(url_value, list):
                    for item in url_value:
                        if isinstance(item, str) and item.startswith(("http://", "https://")):
                            urls.append(item)

        return urls

    def _validate_ip_access(self, hostname: str) -> Dict[str, Any]:
        """验证IP地址访问权限"""
        if not hostname:
            no_hostname_message = self._i18n_manager.t("network.no_hostname")
            return {"allowed": True, "reason": no_hostname_message}

        try:
            # 尝试解析IP地址
            ip = ipaddress.ip_address(hostname)

            # 检查是否在阻止的IP范围内
            for blocked_range in self.blocked_ip_ranges:
                if ip in blocked_range:
                    ip_blocked_message = self._i18n_manager.t(
                        "network.ip_in_blocked_range", range=str(blocked_range)
                    )
                    return {"allowed": False, "reason": ip_blocked_message}

            ip_allowed_message = self._i18n_manager.t("network.ip_address_allowed")
            return {"allowed": True, "reason": ip_allowed_message}

        except ValueError:
            # 不是IP地址，可能是域名
            try:
                # 尝试DNS解析
                resolved_ip = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(resolved_ip)

                for blocked_range in self.blocked_ip_ranges:
                    if ip in blocked_range:
                        resolved_ip_blocked_message = self._i18n_manager.t(
                            "network.resolved_ip_blocked", ip=resolved_ip, range=str(blocked_range)
                        )
                        return {"allowed": False, "reason": resolved_ip_blocked_message}

                resolved_ip_allowed_message = self._i18n_manager.t(
                    "network.resolved_ip_allowed", ip=resolved_ip
                )
                return {"allowed": True, "reason": resolved_ip_allowed_message}

            except (socket.gaierror, ValueError):
                cannot_resolve_message = self._i18n_manager.t("network.cannot_resolve_hostname")
                return {"allowed": True, "reason": cannot_resolve_message}
