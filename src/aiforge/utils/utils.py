import time
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import html
import unicodedata


def clean_text(text):
    """清理乱码文本，更少地过滤有效字符"""
    if not text:
        return ""
    try:
        # 如果是字节串，尝试解码
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")

        # 处理常见的 Unicode 转义序列，这可能表示乱码文本
        # 例如，字符串中可能出现 "\xef\xbb\xbf" 这样的内容
        try:
            if "\\x" in text:
                # 尝试解码常见的有问题字节序列
                text = (
                    text.encode("utf-8")
                    .decode("unicode_escape")
                    .encode("latin1")
                    .decode("utf-8", errors="ignore")  # 添加 errors='ignore'
                )
        except Exception:
            pass  # 如果解码失败，保留原始文本

        # 移除 Unicode 分类为 'C' (Other) 的字符，这通常包括控制字符、格式字符、未分配字符和私用字符。
        # 这种方式对于移除真正不可打印/不可见的字符来说通常是安全的。
        # 同时排除行分隔符 (Zl) 和段落分隔符 (Zp)
        text = "".join(
            char for char in text if unicodedata.category(char)[0] not in ["C", "Zl", "Zp"]
        )

        # 可选：移除未被解析的 HTML 实体，例如 "&#x200B;" 或其他具名实体
        text = re.sub(r"&#x[0-9a-fA-F]+;", "", text)  # 移除 HTML 数字字符引用
        text = re.sub(r"&[a-zA-Z]+;", "", text)  # 移除 HTML 具名字符引用

        # 将多个空格替换为单个空格，并移除首尾空格
        text = re.sub(r"\s+", " ", text).strip()

        return text.strip()
    except Exception:
        return ""


def clean_date_text(i18n_manager, text):
    """专为日期清理文本，保留日期格式关键字符"""
    if not text:
        return ""
    try:
        # 如果是纯数字字符串，直接返回，避免不必要的清理
        if isinstance(text, (int, float)):
            return str(text)
        if isinstance(text, str) and text.isdigit():
            return text

        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="ignore")
        text = html.unescape(text)

        # 获取国际化的日期前缀模式
        date_prefixes = i18n_manager.t(
            "datetime.date_prefixes",
            default=[
                "Posted on",
                "Published on",
                "Date",
                "Updated",
                "Created",
                "Published",
                "Last modified",
                "Time",
            ],
        )

        # 构建动态的前缀正则表达式
        prefix_pattern = "|".join(re.escape(prefix) for prefix in date_prefixes)
        text = re.sub(
            rf"^({prefix_pattern}):\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        text = "".join(char for char in text if unicodedata.category(char)[0] != "C")
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception:
        return ""


def is_valid_date(i18n_manager, date_str, timestamp=None):
    """验证日期字符串是否可转换为有效日期"""
    if not date_str:
        return False

    # 获取国际化的"未知"标识符
    unknown_identifiers = i18n_manager.t(
        "datetime.unknown_identifiers", default=["unknown", "none", "n/a", "null", "None"]
    )

    if str(date_str).lower() in [identifier.lower() for identifier in unknown_identifiers]:
        return False

    date_str = clean_date_text(i18n_manager, str(date_str))

    if timestamp is None:
        timestamp = time.time()

    # 获取国际化的日期验证模式
    date_patterns = i18n_manager.t("datetime.validation_patterns")

    for pattern in date_patterns:
        if re.search(pattern, date_str, re.IGNORECASE):
            return True

    return False


def calculate_actual_date(i18n_manager, pub_time, timestamp):
    """将发布日期转换为 datetime 对象"""
    if not pub_time or not timestamp:
        return None

    try:
        pub_time_cleaned = clean_date_text(i18n_manager, str(pub_time))
        reference_date = datetime.fromtimestamp(timestamp)

        # 优先处理 Unix 时间戳
        if re.match(r"^\d{10}$", pub_time_cleaned):
            return datetime.fromtimestamp(int(pub_time_cleaned))
        if re.match(r"^\d{13}$", pub_time_cleaned):
            return datetime.fromtimestamp(int(pub_time_cleaned) / 1000)

        # 1. 获取国际化的相对时间模式
        relative_patterns_config = i18n_manager.t("datetime.relative_time_patterns")

        # 处理数字相对时间
        numeric_relative_mapping = {
            "seconds_ago": lambda n: reference_date - timedelta(seconds=n),
            "minutes_ago": lambda n: reference_date - timedelta(minutes=n),
            "hours_ago": lambda n: reference_date - timedelta(hours=n),
            "days_ago": lambda n: reference_date - timedelta(days=n),
            "weeks_ago": lambda n: reference_date - timedelta(weeks=n),
            "months_ago": lambda n: reference_date - relativedelta(months=n),
            "years_ago": lambda n: reference_date - relativedelta(years=n),
        }

        for time_unit, calc_func in numeric_relative_mapping.items():
            patterns = relative_patterns_config.get(time_unit, [])
            for pattern in patterns:
                match = re.search(pattern, pub_time_cleaned, re.IGNORECASE)
                if match:
                    num = int(match.group(1))
                    return calc_func(num)

        # 2. 处理特殊相对时间
        special_relative_mapping = {
            "just_now": reference_date,
            "today": reference_date.replace(hour=0, minute=0, second=0, microsecond=0),
            "yesterday": reference_date - timedelta(days=1),
            "day_before_yesterday": reference_date - timedelta(days=2),
        }

        for time_key, calc_date in special_relative_mapping.items():
            keywords = relative_patterns_config.get(time_key, [])
            for keyword in keywords:
                if keyword in pub_time_cleaned:
                    return calc_date

        # 3. 英文相对时间
        english_relative = [
            (r"(\d+)\s*seconds?\s*ago", lambda n: reference_date - timedelta(seconds=n)),
            (r"(\d+)\s*minutes?\s*ago", lambda n: reference_date - timedelta(minutes=n)),
            (r"(\d+)\s*hours?\s*ago", lambda n: reference_date - timedelta(hours=n)),
            (r"(\d+)\s*days?\s*ago", lambda n: reference_date - timedelta(days=n)),
            (r"(\d+)\s*weeks?\s*ago", lambda n: reference_date - timedelta(weeks=n)),
            (r"(\d+)\s*months?\s*ago", lambda n: reference_date - relativedelta(months=n)),
            (r"(\d+)\s*years?\s*ago", lambda n: reference_date - relativedelta(years=n)),
            (r"yesterday", lambda: reference_date - timedelta(days=1)),
            (r"just\s*now", lambda: reference_date),
            (r"last\s*week", lambda: reference_date - timedelta(weeks=1)),
            (r"last\s*month", lambda: reference_date - relativedelta(months=1)),
            (r"last\s*year", lambda: reference_date - relativedelta(years=1)),
        ]

        for pattern, calc_func in english_relative:
            match = re.search(pattern, pub_time_cleaned, re.IGNORECASE)
            if match:
                if match.groups():
                    num = int(match.group(1))
                    return calc_func(num)
                return calc_func()

        # 4. 不完整日期处理
        incomplete_patterns = i18n_manager.t("datetime.incomplete_patterns")

        for pattern in incomplete_patterns:
            match = re.search(pattern, pub_time_cleaned)
            if match:
                month, day = map(int, match.groups())
                if 1 <= month <= 12 and 1 <= day <= 31:
                    current_year = reference_date.year
                    try_date = reference_date.replace(year=current_year, month=month, day=day)
                    if try_date > reference_date:
                        try_date = try_date.replace(year=current_year - 1)
                    if abs((try_date - reference_date).days) > 365:
                        try_date_alt = try_date.replace(
                            year=current_year - 1 if try_date > reference_date else current_year + 1
                        )
                        if abs((try_date_alt - reference_date).days) < abs(
                            (try_date - reference_date).days
                        ):
                            try_date = try_date_alt
                    return try_date

        # 5. 完整日期处理
        complete_patterns_config = i18n_manager.t("datetime.complete_patterns")

        for pattern_config in complete_patterns_config:
            pattern = pattern_config["pattern"]
            date_format = pattern_config["format"]
            match = re.search(pattern, pub_time_cleaned)
            if match:
                try:
                    if len(match.groups()) == 3:
                        date_str = (
                            f"{match.group(1).zfill(2)}/{match.group(2).zfill(2)}/{match.group(3)}"
                        )
                    else:
                        date_str = match.group(0)
                    return datetime.strptime(date_str, date_format)
                except ValueError:
                    continue

    except Exception:
        return None

    return None


def is_within_days(i18n_manager, date_str, days=7):
    """检查日期是否在指定天数内"""
    if not date_str:
        return False
    try:
        timestamp = parse_date_to_timestamp(i18n_manager, date_str)
        if timestamp == 0:
            return False
        days_ago = (datetime.now() - timedelta(days=days)).timestamp()
        return timestamp >= days_ago
    except Exception as e:  # noqa 841
        return False


def parse_date_to_timestamp(i18n_manager, date_str):
    """将日期字符串转换为时间戳用于排序，增加更多日期格式识别"""
    if not date_str:
        return 0

    # 获取国际化的日期前缀
    date_prefixes = i18n_manager.t("datetime.date_prefixes")

    # 预处理常见的非标准字符和修饰语
    date_str = re.sub(r"\(.*?\)", "", date_str).strip()

    # 获取国际化的字符替换规则
    char_replacements = i18n_manager.t("datetime.char_replacements", default={"/": "-"})

    for old_char, new_char in char_replacements.items():
        date_str = date_str.replace(old_char, new_char)

    # 构建动态的前缀正则表达式
    prefix_pattern = "|".join(re.escape(prefix) for prefix in date_prefixes)
    date_str = re.sub(
        rf"^({prefix_pattern}):\s*",
        "",
        date_str,
        flags=re.IGNORECASE,
    ).strip()

    date_str = re.sub(r"[^\d\s\-:]", "", date_str)
    date_str = date_str.split("T")[0]

    # 获取国际化的日期格式
    formats = i18n_manager.t(
        "datetime.parse_formats",
        default=[
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y%m%d",
            "%m-%d-%Y",
            "%B %d, %Y",
            "%d %B %Y",
            "%Y.%m.%d",
            "%y-%m-%d",
        ],
    )

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.timestamp()
        except ValueError:
            continue

    return 0
