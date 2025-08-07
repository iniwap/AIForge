import os
import locale
from typing import Optional


class LocaleDetector:
    @staticmethod
    def detect_from_env() -> Optional[str]:
        """从环境变量检测语言设置"""
        # 检查AIForge特定的环境变量
        aiforge_locale = os.environ.get("AIFORGE_LOCALE") or os.environ.get("AIFORGE_LANG")
        if aiforge_locale:
            return aiforge_locale.split(".")[0].split("_")[0].lower()

        # 检查标准环境变量
        for env_var in ["LANG", "LC_ALL", "LC_MESSAGES"]:
            if env_var in os.environ:
                lang = os.environ[env_var].split(".")[0].split("_")[0]
                return lang.lower()

        return None

    @staticmethod
    def detect_system_locale() -> str:
        """检测系统语言环境"""
        try:
            # 使用新的推荐方法替代 getdefaultlocale()
            current_locale = locale.getlocale()
            if current_locale[0]:
                return current_locale[0].split("_")[0].lower()

            # 如果 getlocale() 返回 None，尝试设置默认locale并获取
            try:
                locale.setlocale(locale.LC_ALL, "")
                current_locale = locale.getlocale()
                if current_locale[0]:
                    return current_locale[0].split("_")[0].lower()
            except locale.Error:
                pass

        except Exception:
            pass

        return "en"  # 默认英文
