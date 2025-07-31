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
        # 例如，字符串中可能出现 "\\xef\\xbb\\xbf" 这样的内容
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


def clean_date_text(text):
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
        text = re.sub(
            r"^(发表于|更新时间|发布时间|创建时间|Posted on|Published on|Date):\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        text = "".join(char for char in text if unicodedata.category(char)[0] != "C")
        # 保留单个空格，避免破坏中文日期格式
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception:
        return ""


def is_valid_date(date_str, timestamp=None):
    """验证日期字符串是否可转换为有效日期"""
    if not date_str or date_str in [None, "", "None", "未知"]:
        return False

    date_str = clean_date_text(str(date_str))

    if timestamp is None:
        timestamp = time.time()

    date_patterns = [
        # 完整日期时间（支持带空格的中文格式）
        r"\d{4}\s*[-/年\.]?\s*\d{1,2}\s*[-/月\.]?\s*\d{1,2}\s*(?:日)?(?:\s+\d{1,2}:\d{1,2}(?::\d{1,2})?)?",  # noqa 501
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?",
        r"\d{1,2}[-/]\d{1,2}[-/]\d{4}\s+\d{1,2}:\d{1,2}(?::\d{1,2})?",
        # 完整日期
        r"\d{4}\s*[-/年\.]?\s*\d{1,2}\s*[-/月\.]?\s*\d{1,2}\s*(?:日)?",
        r"\d{1,2}[-/]\d{1,2}[-/]\d{4}",
        # 相对时间
        r"(\d+)\s*(秒|分钟|分|小时|个小时|天|日|周|星期|个月|月|年)前",
        r"(刚刚|今天|昨天|前天|上周|上星期|上个月|上月|去年)",
        # 不完整日期
        r"\d{1,2}\s*[-/\.月]?\s*\d{1,2}\s*(?:日)?",
        # Unix 时间戳
        r"^\d{10}$",
        r"^\d{13}$",
        # 英文格式
        r"\d+\s*(second|seconds|minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)\s*ago",  # noqa 501
        r"(yesterday|today|just\s*now|last\s*(week|month|year)|this\s*(week|month|year))",
    ]

    for pattern in date_patterns:
        if re.search(pattern, date_str, re.IGNORECASE):
            return True

    return False


def calculate_actual_date(pub_time, timestamp):
    """将发布日期转换为 datetime 对象"""
    if not pub_time or not timestamp:
        return None

    try:
        pub_time_cleaned = clean_date_text(str(pub_time))
        reference_date = datetime.fromtimestamp(timestamp)

        # 优先处理 Unix 时间戳 (修正后的位置)
        if re.match(r"^\d{10}$", pub_time_cleaned):
            return datetime.fromtimestamp(int(pub_time_cleaned))
        if re.match(r"^\d{13}$", pub_time_cleaned):
            return datetime.fromtimestamp(int(pub_time_cleaned) / 1000)

        # 1. 相对时间
        relative_patterns = [
            (r"(\d+)\s*秒前", lambda n: reference_date - timedelta(seconds=n)),
            (r"(\d+)\s*(分钟|分)前", lambda n: reference_date - timedelta(minutes=n)),
            (r"(\d+)\s*(小时|个小时)前", lambda n: reference_date - timedelta(hours=n)),
            (r"(\d+)\s*(天|日)前", lambda n: reference_date - timedelta(days=n)),
            (r"(\d+)\s*(周|星期)前", lambda n: reference_date - timedelta(weeks=n)),
            (r"(\d+)\s*(个月|月)前", lambda n: reference_date - relativedelta(months=n)),
            (r"(\d+)\s*年前", lambda n: reference_date - relativedelta(years=n)),
        ]

        for pattern, calc_func in relative_patterns:
            match = re.search(pattern, pub_time_cleaned, re.IGNORECASE)
            if match:
                num = int(match.group(1))
                return calc_func(num)

        # 2. 特殊相对时间
        special_relative = {
            "刚刚": reference_date,
            "今天": reference_date.replace(hour=0, minute=0, second=0, microsecond=0),
            "昨天": reference_date - timedelta(days=1),
            "前天": reference_date - timedelta(days=2),
            "上周": reference_date - timedelta(weeks=1),
            "上星期": reference_date - timedelta(weeks=1),
            "上个月": reference_date - relativedelta(months=1),
            "上月": reference_date - relativedelta(months=1),
            "去年": reference_date - relativedelta(years=1),
        }

        for key, calc_date in special_relative.items():
            if key in pub_time_cleaned:
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

        # 4. 不完整日期
        incomplete_patterns = [
            r"(\d{1,2})\s*[-/\.月]?\s*(\d{1,2})\s*(?:日)?",
        ]

        for pattern in incomplete_patterns:
            match = re.search(pattern, pub_time_cleaned)
            if match:
                month, day = map(int, match.groups())
                if 1 <= month <= 12 and 1 <= day <= 31:
                    current_year = reference_date.year
                    try_date = reference_date.replace(year=current_year, month=month, day=day)
                    if try_date > reference_date:
                        try_date = try_date.replace(year=current_year - 1)
                    # 验证日期合理性
                    if abs((try_date - reference_date).days) > 365:
                        try_date_alt = try_date.replace(
                            year=current_year - 1 if try_date > reference_date else current_year + 1
                        )
                        if abs((try_date_alt - reference_date).days) < abs(
                            (try_date - reference_date).days
                        ):
                            try_date = try_date_alt
                    return try_date

        # 5. 完整日期
        complete_patterns = [
            (r"(\d{4})\s*[-/年\.]?\s*\d{1,2}\s*[-/月\.]?\s*\d{1,2}\s*(?:日)?", "%Y-%m-%d"),
            (r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", "%m/%d/%Y"),
        ]

        for pattern, date_format in complete_patterns:
            match = re.search(pattern, pub_time_cleaned)
            if match:
                date_str = match.group(0)
                return datetime.strptime(date_str, date_format)

    except Exception:
        return None

    return None


def is_within_days(date_str, days=7):
    """检查日期是否在指定天数内"""
    if not date_str:
        return False
    try:
        timestamp = parse_date_to_timestamp(date_str)
        if timestamp == 0:
            return False
        days_ago = (datetime.now() - timedelta(days=days)).timestamp()
        return timestamp >= days_ago
    except Exception as e:  # noqa 841
        return False


def parse_date_to_timestamp(date_str):
    """将日期字符串转换为时间戳用于排序，增加更多日期格式识别"""
    if not date_str:
        return 0

    # 预处理常见的非标准字符和修饰语
    # 移除括号及其内容，例如 "(发布时间)"
    date_str = re.sub(r"\(.*?\)", "", date_str).strip()
    date_str = date_str.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-")
    # 移除常见的日期前缀或无关文本，但保留日期本身
    date_str = re.sub(
        r"^(发表于|更新时间|发布时间|创建时间|Posted on|Published on|Date):\s*",
        "",
        date_str,
        flags=re.IGNORECASE,
    ).strip()
    date_str = re.sub(
        r"[^\d\s\-:]", "", date_str
    )  # 移除多余的非日期字符，但保留数字、空格、连字符、冒号
    date_str = date_str.split("T")[
        0
    ]  # 通常时间戳格式的'T'后面是时间，我们只取日期部分，但确保不会切掉只有日期部分的时间

    # 尝试匹配更广泛的日期时间格式
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y%m%d",  # 例如 20240530
        "%m-%d-%Y",  # 例如 05-30-2024
        "%B %d, %Y",  # 例如 May 30, 2024 (如果文本是英文)
        "%d %B %Y",  # 例如 30 May 2024 (如果文本是英文)
        "%Y.%m.%d",  # 例如 2024.05.30
        "%y-%m-%d",  # 例如 24-05-30
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.timestamp()
        except ValueError:
            continue

    return 0
