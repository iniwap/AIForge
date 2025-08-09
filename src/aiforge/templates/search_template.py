# -*- coding: utf-8 -*-
# Author: iniwap
# Date: 2025-06-03
# Description: 用于本地搜索，关注项目 https://github.com/iniwap/ai_write_x

# 版权所有 (c) 2025 iniwap
# 本文件受 AIWriteX 附加授权条款约束，不可单独使用、传播或部署。
# 禁止在未经作者书面授权的情况下将本文件用于商业服务、分发或嵌入产品。
# 如需授权，请联系 iniwaper@gmail.com 或 522765228@qq.com
# AIWriteX授权协议请见https://github.com/iniwap/ai_write_x LICENSE 和 NOTICE 文件。


import time
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from datetime import datetime, timedelta
import concurrent.futures
from ..utils import utils
from ..strategies.search_template_strategy import StandardTemplateStrategy
from ..utils.progress_indicator import ProgressIndicator
from ..i18n.manager import AIForgeI18nManager


def get_template_guided_search_instruction(
    search_query,
    expected_output,
    max_results=10,
    min_abstract_len=300,
):
    # 动态生成返回格式
    data_format = StandardTemplateStrategy().generate_format(expected_output, min_abstract_len)

    # 获取本地化的搜索指令模板
    search_instruction_template = AIForgeI18nManager.get_instance().t(
        "search.guided_instruction_template"
    )

    search_instruction = search_instruction_template.format(
        data_format=data_format, search_query=search_query, max_results=max_results
    )

    return search_instruction


def get_free_form_ai_search_instruction(
    search_query,
    expected_output,
    max_results=10,
    min_abstract_len=300,
):
    # 动态生成返回格式
    data_format = StandardTemplateStrategy().generate_format(
        expected_output, min_abstract_len, is_free_form=True
    )

    # 获取本地化的自由形式搜索指令模板
    search_instruction_template = AIForgeI18nManager.get_instance().t(
        "search.free_form_instruction_template"
    )

    search_instruction = search_instruction_template.format(
        data_format=data_format,
        search_query=search_query,
        max_results=max_results,
        min_abstract_len=min_abstract_len,
    )

    return search_instruction


LOCALE_SEARCH_ENGINES = {
    "zh": ["baidu", "bing", "360", "sogou"],
    "en": ["google", "bing", "duckduckgo"],
    "ar": ["google", "bing", "duckduckgo"],
    "de": ["google", "bing", "startpage"],
    "es": ["google", "bing", "duckduckgo"],
    "fr": ["google", "bing", "startpage"],
    "hi": ["google", "bing", "duckduckgo"],
    "ja": ["yahoo_japan", "google", "bing"],
    "ko": ["naver", "google", "bing"],
    "pt": ["google", "bing", "duckduckgo"],
    "ru": ["yandex", "google", "bing"],
    "vi": ["google", "bing", "duckduckgo"],
}


def search_web(
    search_query, max_results=10, min_items=1, min_abstract_len=300, max_abstract_len=1000
):
    """使用多个搜索引擎进行网络搜索，返回min_items有效结果"""
    i18n_manager = AIForgeI18nManager.get_instance()
    for engine in LOCALE_SEARCH_ENGINES.get(i18n_manager.locale, "zh"):
        try:
            engine_name = i18n_manager.t(f"search.engine_{engine}")
            ProgressIndicator.get_instance().show_search_process(engine_name)

            search_result = _search_template(
                search_query,
                max_results,
                ENGINE_CONFIGS[engine],
                min_abstract_len,
                max_abstract_len,
            )
            # 验证搜索结果质量
            if validate_search_result(search_result, min_items):
                return search_result
            else:
                continue
        except Exception:
            continue

    # 所有搜索引擎都失败，返回 None
    return None


def validate_search_result(result, min_items=1, search_type="local", min_abstract_len=300):
    """验证搜索结果质量，确保至少min_results条结果满足指定搜索类型的完整性条件，并返回转换后的日期格式"""
    if not isinstance(result, dict) or not result.get("success", False):
        return False

    results = result.get("results", [])
    if not results or len(results) < min_items:
        return False

    timestamp = result.get("timestamp", time.time())
    i18n_manager = AIForgeI18nManager.get_instance()
    date_patterns = i18n_manager.t("datetime.date_patterns", default=[])
    for item in results:
        pub_time = item.get("pub_time", "")
        abstract = item.get("abstract", "")

        # 尝试从 pub_time 转换
        if pub_time:
            if re.match(r"^\d{4}-\d{2}-\d{2}$", pub_time):
                try:
                    datetime.strptime(pub_time, "%Y-%m-%d")
                    continue
                except ValueError:
                    pass
            # 处理带时分秒的格式
            if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?$", pub_time):
                try:
                    actual_date = datetime.strptime(pub_time, "%Y-%m-%d %H:%M:%S")
                    item["pub_time"] = actual_date.strftime("%Y-%m-%d")
                    continue
                except ValueError:
                    try:
                        actual_date = datetime.strptime(pub_time, "%Y-%m-%d %H:%M")
                        item["pub_time"] = actual_date.strftime("%Y-%m-%d")
                        continue
                    except ValueError:
                        pass
            if timestamp:
                try:
                    actual_date = utils.calculate_actual_date(pub_time, timestamp)
                    if actual_date:
                        item["pub_time"] = actual_date.strftime("%Y-%m-%d")
                    else:
                        item["pub_time"] = ""
                except Exception:
                    item["pub_time"] = ""

        # 兜底：从 abstract 提取日期
        if not item["pub_time"] and abstract:
            for pattern in date_patterns:
                match = re.search(pattern, abstract, re.IGNORECASE)
                if match:
                    pub_time = match.group(0)
                    if utils.is_valid_date(pub_time):
                        pub_time_date = utils.calculate_actual_date(pub_time, timestamp)
                        if pub_time_date:
                            item["pub_time"] = pub_time_date.strftime("%Y-%m-%d")
                            break

    validation_rules = {
        "local": ["title", "url", "abstract", "pub_time"],
        "ai_guided": ["title", "url", "abstract"],
        "ai_free": ["title", "abstract"],
        "reference_article": ["title", "url", "content", "pub_time"],
    }

    quality_rules = {
        "local": {
            "abstract_min_length": min_abstract_len,
            "require_valid_date": True,
        },
        "ai_guided": {
            "abstract_min_length": min_abstract_len / 2,
            "require_valid_date": True,
        },
        "ai_free": {
            "abstract_min_length": min_abstract_len / 4,
            "require_valid_date": False,
        },
        "reference_article": {
            "content_min_length": min_abstract_len,
            "require_valid_date": True,
        },
    }

    required_fields = validation_rules.get(search_type, validation_rules["local"])
    quality_req = quality_rules.get(search_type, quality_rules["local"])

    for item in results:
        if not all(item.get(field, "").strip() for field in required_fields):
            continue

        # 针对 reference_article 类型的特殊处理
        if search_type == "reference_article":
            content = item.get("content", "")
            if len(content.strip()) < quality_req["content_min_length"]:
                continue
        else:
            # 其他类型检查 abstract
            abstract = item.get("abstract", "")
            if len(abstract.strip()) < quality_req.get("abstract_min_length", 0):
                continue

        if quality_req["require_valid_date"] and search_type != "ai_guided":
            pub_time = item.get("pub_time", "")
            if not pub_time or not re.match(r"^\d{4}-\d{2}-\d{2}$", pub_time):
                continue
            try:
                datetime.strptime(pub_time, "%Y-%m-%d")
            except ValueError:
                continue

        return True

    return False


def get_common_headers():
    """获取通用请求头"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # noqa 501
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def _extract_publish_time(page_soup):
    """统一的发布时间提取函数"""
    # Meta 标签提取 - 优先处理标准的发布时间标签
    i18n_manager = AIForgeI18nManager.get_instance()
    meta_selectors = i18n_manager.t("datetime.meta_selectors")
    timezone_offset = i18n_manager.t("datetime.timezone_offset", default=8)
    for selector in meta_selectors:
        meta_tag = page_soup.select_one(selector)
        if meta_tag:
            datetime_str = meta_tag.get("content")
            if datetime_str:
                try:
                    # 处理 UTC 时间 (以Z结尾)
                    if datetime_str.endswith("Z"):
                        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                        dt_local = dt + timedelta(hours=int(timezone_offset))
                        return dt_local.strftime(
                            i18n_manager.t("datetime.date_format", default="%Y-%m-%d")
                        )
                    # 处理带时区的 ISO 8601 格式
                    elif "T" in datetime_str and ("+" in datetime_str or "-" in datetime_str[-6:]):
                        dt = datetime.fromisoformat(datetime_str)
                        return dt.strftime("%Y-%m-%d")
                    # 处理简单的日期格式
                    elif "T" in datetime_str:
                        return datetime_str.split("T")[0]
                except Exception:
                    pass

    # Time 标签提取
    time_tags = page_soup.select("time")
    for time_tag in time_tags:
        datetime_attr = time_tag.get("datetime")
        if datetime_attr:
            try:
                # 处理 UTC 时间 (以Z结尾)
                if datetime_attr.endswith("Z"):
                    dt = datetime.fromisoformat(datetime_attr.replace("Z", "+00:00"))
                    # 转换为东八区时间
                    dt_local = dt + timedelta(hours=8)
                    return dt_local.strftime("%Y-%m-%d")
                # 处理带时区的 ISO 8601 格式
                elif "T" in datetime_attr and ("+" in datetime_attr or "-" in datetime_attr[-6:]):
                    dt = datetime.fromisoformat(datetime_attr)
                    return dt.strftime("%Y-%m-%d")
                # 处理简单的日期格式
                elif "T" in datetime_attr:
                    return datetime_attr.split("T")[0]
            except Exception:
                pass

        # 如果 datetime 属性解析失败，尝试文本内容
        text_content = utils.clean_date_text(time_tag.get_text())
        if text_content and utils.is_valid_date(text_content):
            time_date = utils.calculate_actual_date(text_content, time.time())
            if time_date:
                return time_date.strftime("%Y-%m-%d")

    # HTML 元素提取
    date_selectors = [
        "textarea.article-time",
        "[class*='date']",
        "[class*='time']",
        "[class*='publish']",
        "[class*='post-date']",
        "[id*='date']",
        "[id*='time']",
        ".byline",
        ".info",
        ".article-meta",
        ".source",
        ".entry-date",
        "div.date",
        "p.date",
        "p.time",
    ]

    for selector in date_selectors:
        elements = page_soup.select(selector)
        for elem in elements:
            text = utils.clean_date_text(elem.get_text())
            if text and utils.is_valid_date(text):
                elem_date = utils.calculate_actual_date(text, time.time())
                if elem_date:
                    return elem_date.strftime("%Y-%m-%d")

    # 兜底：全文搜索
    text = utils.clean_date_text(page_soup.get_text())
    fallback_patterns = i18n_manager.t("datetime.fallback_patterns", default=[])
    for pattern in fallback_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            pub_time = match.group(0)
            if utils.is_valid_date(pub_time):
                pub_time_date = utils.calculate_actual_date(pub_time, time.time())
                if pub_time_date:
                    return pub_time_date.strftime("%Y-%m-%d")

    return ""


def extract_page_content(url, headers=None):
    """从 URL 提取页面内容和发布日期"""
    try:
        time.sleep(1)
        response = requests.get(url, headers=headers or {}, timeout=30)
        response.encoding = response.apparent_encoding or "utf-8"
        content = response.text

        page_soup = BeautifulSoup(content, "html.parser")

        # 直接调用统一的时间提取函数
        pub_time = _extract_publish_time(page_soup)

        return page_soup, pub_time

    except Exception:
        return None, None


def enhance_abstract(abstract, page_soup, min_abstract_len=300, max_abstract_len=1000):
    """
    增强摘要内容，从原文提取。
    如果 _extract_full_article_content 的内容长度 >= min_abstract_len
    否则，结合原始摘要，确保总长度不超过 max_abstract_len
    """
    if not page_soup:
        return abstract

    # 提取正文
    article = extract_full_article_content(page_soup, min_abstract_len)

    if article:
        # 检查正文长度是否满足 min_abstract_len
        if len(article) >= min_abstract_len:
            # 直接返回正文，截取至 max_abstract_len
            return article[:max_abstract_len].strip()
        else:
            # 清理原始摘要，结合正文
            return (abstract + " " + article)[:max_abstract_len].strip()

    # 回退到原始摘要
    return abstract


def sort_and_filter_results(results):
    if not results:
        return results

    recent_results = []
    for result in results:
        pub_time = result.get("pub_time")
        if pub_time is None or utils.is_within_days(pub_time, 7):
            recent_results.append(result)

    recent_results.sort(
        key=lambda x: (
            x.get("pub_time") is None,
            -(utils.parse_date_to_timestamp(x.get("pub_time", "")) or 0),
        )
    )

    return recent_results


def _search_template(
    search_query, max_results, engine_config, min_abstract_len=300, max_abstract_len=1000
):
    """通用搜索模板"""

    try:
        results = []
        headers = get_common_headers()
        search_url = engine_config["url"].format(
            search_query=quote(search_query), max_results=max_results
        )

        response = requests.get(search_url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding or "utf-8"
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # 查找结果容器
        search_results = []
        for selector in engine_config["result_selectors"]:
            search_results = soup.select(selector)
            if search_results:
                break

        if not search_results:
            return {
                "timestamp": time.time(),
                "search_query": search_query,
                "results": [],
                "success": False,
                "error": AIForgeI18nManager.get_instance().t("search.no_valid_results"),
            }

        # 收集结果和需要抓取的URL
        tasks = []
        parsed_results = []
        for result in search_results[:max_results]:
            try:
                # 提取标题
                title_elem = None
                for selector in engine_config["title_selectors"]:
                    title_elem = result.select_one(selector)
                    if title_elem:
                        break
                if not title_elem:
                    continue

                link_elem = (
                    title_elem
                    if title_elem.name == "a"
                    else title_elem.find("a") or result.select_one("a[href]")
                )
                if not link_elem:
                    continue

                title = utils.clean_text(title_elem.get_text().strip()) or "no title"
                url = link_elem.get("href", "")

                # 处理重定向链接
                if (
                    engine_config.get("redirect_pattern")
                    and engine_config["redirect_pattern"] in url
                ):
                    try:
                        response = requests.head(
                            url, headers=headers, allow_redirects=True, timeout=5
                        )
                        response.raise_for_status()
                        url = response.url
                    except requests.exceptions.RequestException:
                        url = ""

                # 提取摘要
                abstract = ""
                for selector in engine_config["abstract_selectors"]:
                    abstract_elem = result.select_one(selector)
                    if abstract_elem:
                        abstract = utils.clean_text(abstract_elem.get_text().strip())
                        if len(abstract) > 20:
                            break
                if not abstract and engine_config.get("fallback_abstract"):
                    abstract_elem = result.find(string=True, recursive=True)
                    abstract = (
                        utils.clean_text(abstract_elem.strip())[:max_abstract_len]
                        if abstract_elem
                        else ""
                    )

                parsed_results.append({"title": title, "url": url, "abstract": abstract})
                if url and url.startswith("http"):
                    tasks.append((url, headers))

            except Exception:
                continue

        # 并行获取页面内容
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_results, 5)) as executor:
            future_to_url = {
                executor.submit(extract_page_content, url, headers): url for url, headers in tasks
            }
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    page_soup, pub_time = future.result()
                    for res in parsed_results:
                        if res["url"] == url:
                            res["pub_time"] = pub_time
                            res["abstract"] = (
                                enhance_abstract(
                                    res["abstract"], page_soup, min_abstract_len, max_abstract_len
                                )
                                or res["abstract"]
                            )

                            break
                except Exception:
                    pass

        # 构建最终结果
        results = [
            {
                "title": res["title"],
                "url": res["url"],
                "abstract": res["abstract"] or "",
                "pub_time": res.get("pub_time", None),
            }
            for res in parsed_results
            if res["title"] and res["url"]
        ]
        results = sort_and_filter_results(results)

        return {
            "timestamp": time.time(),
            "search_query": search_query,
            "results": results,
            "success": bool(results),
            "error": (
                None if results else AIForgeI18nManager.get_instance().t("search.no_valid_results")
            ),
        }

    except Exception as e:
        return {
            "timestamp": time.time(),
            "search_query": search_query,
            "results": [],
            "success": False,
            "error": str(e),
        }


# 搜索引擎配置
ENGINE_CONFIGS = {
    "baidu": {
        "url": "https://www.baidu.com/s?wd={search_query}&rn={max_results}",
        "redirect_pattern": "baidu.com/link?url=",
        "result_selectors": [
            "div.result",
            "div.c-container",
            "div[class*='result']",
            "div[tpl]",
            ".c-result",
            "div[mu]",
            ".c-result-content",
            "[data-log]",
            "div.c-row",
            ".c-border",
            "div[data-click]",
            ".result-op",
            "[class*='search']",
            "[class*='item']",
            "article",
            "section",
            "div#content_left div",
            "div.result-c",
            "div.c-abstract",
            "div.result-classic",
            "div.result-new",
            "[data-tuiguang]",
            "div.c-container-new",
            "div.result-item",
            "div.c-frame",
            "div.c-gap",
        ],
        "title_selectors": [
            "h3",
            "h3 a",
            ".t",
            ".c-title",
            "[class*='title']",
            "h3.t",
            ".c-title-text",
            "h3[class*='title']",
            ".result-title",
            "a[class*='title']",
            ".c-link",
            "h1",
            "h2",
            "h4",
            "h5",
            "h6",
            "a[href]",
            ".link",
            ".url",
            ".c-title a",
            ".c-title-new",
            "[data-title]",
            ".c-showurl",
            "div.title a",
        ],
        "abstract_selectors": [
            "span.content-right_8Zs40",
            "div.c-abstract",
            ".c-span9",
            "[class*='abstract']",
            ".c-span-last",
            ".c-summary",
            "div.c-row .c-span-last",
            ".result-desc",
            "[class*='desc']",
            ".c-font-normal",
            "p",
            "div",
            "span",
            ".text",
            ".content",
            "[class*='text']",
            "[class*='content']",
            "[class*='summary']",
            "[class*='excerpt']",
            ".c-abstract-new",
            ".c-abstract-content",
            "div.c-gap-bottom",
            "div.c-span18",
        ],
        "fallback_abstract": False,
    },
    "bing": {
        "url": "https://www.bing.com/search?q={search_query}&count={max_results}",
        "result_selectors": [
            "li.b_algo",
            "div.b_algo",
            "li[class*='algo']",
            ".b_searchResult",
            "[class*='result']",
            ".b_ans",
            ".b_algoheader",
            "li.b_ad",
            ".b_entityTP",
            ".b_rich",
            "[data-bm]",
            ".b_caption",
            "[class*='search']",
            "[class*='item']",
            "article",
            "section",
            "div.b_pag",
            ".b_algoSlug",
            ".b_vList li",
            ".b_resultCard",
            ".b_focusList",
            ".b_answer",
        ],
        "title_selectors": [
            "h2",
            "h3",
            "h2 a",
            "h3 a",
            ".b_title",
            "[class*='title']",
            "h2.b_topTitle",
            ".b_algo h2",
            ".b_entityTitle",
            "a h2",
            ".b_adlabel + h2",
            ".b_promoteText h2",
            "h1",
            "h4",
            "h5",
            "h6",
            "a[href]",
            ".link",
            ".url",
            ".b_title a",
            ".b_caption h2",
            "[data-title]",
            ".b_focusTitle",
        ],
        "abstract_selectors": [
            "p.b_lineclamp4",
            "div.b_caption",
            ".b_snippet",
            "[class*='caption']",
            "[class*='snippet']",
            ".b_paractl",
            ".b_dList",
            ".b_factrow",
            ".b_rich .b_caption",
            ".b_entitySubTypes",
            "p",
            "div",
            "span",
            ".text",
            ".content",
            "[class*='text']",
            "[class*='content']",
            "[class*='summary']",
            "[class*='excerpt']",
            ".b_vPanel",
            ".b_algoSlug",
            ".b_attribution",
        ],
        "fallback_abstract": False,
    },
    "360": {
        "url": "https://www.so.com/s?q={search_query}&pn=1&rn={max_results}",
        "result_selectors": [
            "li.res-list",
            "div.result",
            "li[class*='res']",
            ".res-item",
            "[class*='result']",
            ".res",
            "li.res-top",
            ".res-gap-right",
            "[data-res]",
            ".result-item",
            ".res-rich",
            ".res-video",
            "[class*='search']",
            "[class*='item']",
            "article",
            "section",
            ".res-news",
            ".res-article",
            ".res-block",
            "div.g",
            ".res-container",
        ],
        "title_selectors": [
            "h3.res-title",
            "h3",
            "h3 a",
            ".res-title",
            "[class*='title']",
            "a[class*='title']",
            ".res-title a",
            "h4.res-title",
            ".title",
            ".res-meta .title",
            ".res-rich-title",
            "h1",
            "h2",
            "h4",
            "h5",
            "h6",
            "a[href]",
            ".link",
            ".url",
            ".res-news-title",
            ".res-block-title",
        ],
        "abstract_selectors": [
            "p.res-desc",
            "div.res-desc",
            ".res-summary",
            "[class*='desc']",
            "[class*='summary']",
            ".res-rich-desc",
            ".res-meta",
            ".res-info",
            ".res-rich .res-desc",
            ".res-gap-right p",
            "p",
            "div",
            "span",
            ".text",
            ".content",
            "[class*='text']",
            "[class*='content']",
            "[class*='summary']",
            "[class*='excerpt']",
            ".res-news-desc",
            ".res-block-desc",
        ],
        "fallback_abstract": False,
    },
    "sogou": {
        "url": "https://www.sogou.com/web?query={search_query}",
        "redirect_pattern": "/link?url=",
        "result_selectors": [
            "div.vrwrap",
            "div.results",
            "div.result",
            "[class*='vrwrap']",
            "[class*='result']",
            ".rb",
            ".vrwrap-new",
            ".results-wrapper",
            "[data-md5]",
            ".result-item",
            ".vrwrap-content",
            ".sogou-results",
            "[class*='search']",
            "[class*='item']",
            "article",
            "section",
            ".results-div",
            ".vrwrap-item",
            "div.results > div",
            ".result-wrap",
        ],
        "title_selectors": [
            "h3.vr-title",
            "h3.vrTitle",
            "a.title",
            "h3",
            "a",
            "[class*='title']",
            "[class*='vr-title']",
            "[class*='vrTitle']",
            ".vr-title a",
            ".vrTitle a",
            "h4.vr-title",
            "h4.vrTitle",
            ".result-title",
            ".vrwrap h3",
            ".rb h3",
            ".title-link",
            "h1",
            "h2",
            "h4",
            "h5",
            "h6",
            "a[href]",
            ".link",
            ".url",
            ".vr-title",
        ],
        "abstract_selectors": [
            "div.str-info",
            "div.str_info",
            "p.str-info",
            "p.str_info",
            "div.ft",
            "[class*='str-info']",
            "[class*='str_info']",
            "[class*='abstract']",
            "[class*='desc']",
            ".rb .ft",
            ".vrwrap .ft",
            ".result-desc",
            ".content-info",
            "p",
            "div",
            "span",
            ".text",
            ".content",
            "[class*='text']",
            "[class*='content']",
            "[class*='summary']",
            "[class*='excerpt']",
            ".vr-desc",
        ],
        "fallback_abstract": True,
    },
    "google": {
        "url": "https://www.google.com/search?q={search_query}&num={max_results}",
        "result_selectors": [
            "div.g",
            "div[data-ved]",
            ".g",
            ".tF2Cxc",
            ".hlcw0c",
            "[class*='result']",
            ".rc",
            ".r",
            "div.yuRUbf",
        ],
        "title_selectors": ["h3", "h1", "h2", ".LC20lb", ".DKV0Md", "a h3", ".yuRUbf h3"],
        "abstract_selectors": [
            ".VwiC3b",
            ".s",
            ".st",
            ".IsZvec",
            ".aCOpRe",
            ".yXK7lf",
            "span[data-ved]",
        ],
        "fallback_abstract": False,
    },
    "yandex": {
        "url": "https://yandex.com/search/?text={search_query}&numdoc={max_results}",
        "result_selectors": [
            ".serp-item",
            ".organic",
            ".content",
            ".serp-item_type_search",
            ".serp-list__item",
            ".organic__url-text",
            ".serp-item__wrap",
        ],
        "title_selectors": [
            "h2",
            ".organic__title",
            ".title",
            ".organic__title-wrapper",
            ".serp-item__title",
            "h3",
        ],
        "abstract_selectors": [
            ".text-container",
            ".organic__text",
            ".snippet",
            ".organic__content-wrapper",
            ".serp-item__text",
            ".organic__greenurl",
        ],
        "fallback_abstract": False,
    },
    "naver": {
        "url": "https://search.naver.com/search.naver?query={search_query}&start=1&display={max_results}",  # noqa 501
        "result_selectors": [
            ".bx",
            ".total_wrap",
            ".news_wrap",
            ".api_subject_bx",
            ".total_group",
            ".lst_total",
            ".news_area",
        ],
        "title_selectors": [
            ".news_tit",
            ".total_tit",
            "dt a",
            ".api_txt_lines",
            ".total_group .tit",
            ".lst_total .tit",
        ],
        "abstract_selectors": [
            ".news_dsc",
            ".total_dsc",
            ".dsc_txt",
            ".api_txt_lines",
            ".total_group .dsc",
            ".lst_total .dsc",
        ],
        "fallback_abstract": False,
    },
    "yahoo_japan": {
        "url": "https://search.yahoo.co.jp/search?p={search_query}&n={max_results}",
        "result_selectors": [
            ".sw-CardBase",
            ".algo",
            ".w",
            ".Algo",
            ".compTitle",
            ".searchCenterMiddle li",
        ],
        "title_selectors": [
            "h3",
            ".sw-CardBase__title",
            ".ac",
            ".compTitle h3",
            ".Algo h3",
            "h3 a",
        ],
        "abstract_selectors": [
            ".sw-CardBase__body",
            ".compText",
            ".ab",
            ".Algo .compText",
            ".sw-CardBase .compText",
        ],
        "fallback_abstract": False,
    },
    "duckduckgo": {
        "url": "https://duckduckgo.com/?q={search_query}",
        "result_selectors": ["[data-result]", ".result", ".web-result", ".results_links"],
        "title_selectors": [".result__title", "h2", "h3", ".result__a"],
        "abstract_selectors": [".result__snippet", ".result__body", ".web-result__snippet"],
        "fallback_abstract": False,
    },
    "startpage": {
        "url": "https://www.startpage.com/sp/search?query={search_query}&num={max_results}",
        "result_selectors": [".w-gl__result", ".result", ".search-result"],
        "title_selectors": [".w-gl__result-title", "h3", ".search-result__title"],
        "abstract_selectors": [
            ".w-gl__description",
            ".search-result__body",
            ".w-gl__result-snippet",
        ],
        "fallback_abstract": False,
    },
    "searx": {
        "url": "https://searx.org/search?q={search_query}&format=json",
        "result_selectors": [".result", "article", ".search_result"],
        "title_selectors": ["h3", ".result_title", "h4"],
        "abstract_selectors": [".content", ".result_content", "p"],
        "fallback_abstract": True,
    },
}


def extract_full_article_content(page_soup, min_abstract_len=300):
    """提取完整文章内容，过滤无关信息"""

    # 获取本地化的噪声关键词列表
    noise_keywords = AIForgeI18nManager.get_instance().t("search.noise_keywords", default=[])
    if isinstance(noise_keywords, str):
        noise_keywords = noise_keywords.split(",")

    # 第一步：移除无关元素
    for elem in page_soup.select(
        "script, style, nav, header, footer, aside, .ad, .advertisement, .sidebar, .menu, "
        ".promo, .recommend, .social-share, .footer-links, [class*='banner'], [class*='promo'], "
        "[class*='newsletter'], [class*='signup'], [class*='feedback'], [class*='copyright'], "
        "[id*='footer'], [id*='bottom'], .live-room, .stock-info, .finance-nav, .related-links, "
        ".seo_data_list, .right-side-ad, ins.sinaads, .cj-r-block, [id*='7x24'], .navigation,"
        "[class*='advert'], [class*='social'], .comment, [class*='share'], #commentModule"
    ):
        elem.decompose()

    # 第二步：定义正文选择器
    content_selectors = [
        # === 微信公众号 ===
        "#js_content",  # 微信公众号主要正文容器
        ".rich_media_content",  # 微信公众号富文本内容
        ".rich_media_area_primary",  # 微信公众号主要内容区域
        ".rich_media_wrp",  # 微信公众号包装器
        # === 主流新闻网站 ===
        ".post_body",  # 网易新闻、搜狐新闻
        ".content_area",  # 新浪新闻
        ".article-content",  # 腾讯新闻、凤凰网
        ".art_context",  # 环球网
        ".content",  # 人民网
        ".article_content",  # 中新网
        ".cont",  # 光明网
        ".article-body",  # CNN、NYTimes、BBC等
        ".story-body",  # BBC新闻
        ".story-content",  # The Guardian
        ".entry-content",  # The Washington Post
        ".content__article-body",  # Guardian、Telegraph
        ".js-entry-text",  # Wall Street Journal
        ".story__body",  # Vox、The Verge
        ".ArticleBody",  # Bloomberg
        ".caas-body",  # Yahoo News
        ".RichTextStoryBody",  # Reuters
        ".InlineVideo-container",  # Associated Press
        # === 中文新闻门户 ===
        ".content_box",  # 今日头条
        ".article-detail",  # 百度新闻
        ".news_txt",  # 网易新闻详情
        ".article_txt",  # 搜狐新闻
        ".content_detail",  # 新浪新闻详情
        ".detail-content",  # 澎湃新闻
        ".m-article-content",  # 界面新闻
        ".article-info",  # 财经网
        ".news-content",  # 东方财富
        ".art_con",  # 金融界
        # === 博客平台 ===
        ".post-content",  # WordPress默认
        ".entry-content",  # WordPress主题
        ".post-body",  # Blogger
        ".entry-body",  # Movable Type
        ".post__content",  # Ghost
        ".article__content",  # Medium（部分主题）
        ".post-full-content",  # Ghost主题
        ".kg-card-markdown",  # Ghost Markdown卡片
        ".content-body",  # Drupal
        ".field-name-body",  # Drupal字段
        ".node-content",  # Drupal节点
        # === 技术博客和文档 ===
        ".markdown-body",  # GitHub、GitBook
        ".content",  # GitBook、Read the Docs
        ".document",  # Sphinx文档
        ".main-content",  # Jekyll、Hugo主题
        ".post-content",  # Jekyll默认
        ".content-wrap",  # Hexo主题
        ".article-entry",  # Hexo默认
        ".md-content",  # VuePress
        ".theme-default-content",  # VuePress默认主题
        ".docstring",  # 技术文档
        ".rst-content",  # reStructuredText
        # === 社交媒体和论坛 ===
        ".usertext-body",  # Reddit
        ".md",  # Reddit Markdown
        ".timeline-item",  # GitHub
        ".commit-message",  # GitHub提交信息
        ".blob-wrapper",  # GitHub文件内容
        ".answer",  # Stack Overflow
        ".post-text",  # Stack Overflow问题/答案
        ".question-summary",  # Stack Overflow
        ".js-post-body",  # Stack Overflow
        ".feed-item-content",  # LinkedIn
        ".tweet-text",  # Twitter（旧版）
        ".tweet-content",  # Twitter
        # === 知识问答平台 ===
        ".RichText",  # 知乎
        ".content",  # 知乎回答内容
        ".QuestionRichText",  # 知乎问题描述
        ".AnswerItem",  # 知乎答案
        ".Post-RichText",  # 知乎专栏
        ".ArticleItem-content",  # 知乎文章
        ".answer-content",  # 百度知道
        ".best-text",  # 百度知道最佳答案
        ".wgt-answers",  # 百度知道答案
        # === 电商平台 ===
        ".detail-content",  # 淘宝商品详情
        ".rich-text",  # 京东商品描述
        ".product-detail",  # 亚马逊商品详情
        ".product-description",  # 通用商品描述
        ".item-description",  # eBay商品描述
        # === CMS系统 ===
        ".node-content",  # Drupal
        ".entry-content",  # WordPress
        ".content-area",  # WordPress主题
        ".single-content",  # WordPress单页
        ".page-content",  # WordPress页面
        ".post-entry",  # WordPress主题
        ".article-content",  # Joomla
        ".item-page",  # Joomla文章页
        ".content-inner",  # Joomla内容
        ".story-content",  # ExpressionEngine
        ".channel-entry",  # ExpressionEngine
        # === 企业网站 ===
        ".main-content",  # 通用主内容
        ".content-wrapper",  # 内容包装器
        ".page-content",  # 页面内容
        ".text-content",  # 文本内容
        ".body-content",  # 主体内容
        ".primary-content",  # 主要内容
        ".content-main",  # 主内容区
        ".content-primary",  # 主要内容
        ".main-article",  # 主文章
        ".article-main",  # 文章主体
        # === 学术和教育网站 ===
        ".abstract",  # 学术论文摘要
        ".full-text",  # 全文内容
        ".article-fulltext",  # 学术文章全文
        ".article-body",  # 学术文章主体
        ".paper-content",  # 论文内容
        ".journal-content",  # 期刊内容
        ".course-content",  # 课程内容
        ".lesson-content",  # 课程内容
        ".lecture-notes",  # 讲义笔记
        # === 政府和机构网站 ===
        ".gov-content",  # 政府网站内容
        ".official-content",  # 官方内容
        ".policy-content",  # 政策内容
        ".announcement",  # 公告内容
        ".notice-content",  # 通知内容
        ".regulation-text",  # 法规文本
        # === 多媒体和娱乐 ===
        ".video-description",  # 视频描述
        ".episode-description",  # 剧集描述
        ".movie-synopsis",  # 电影简介
        ".album-description",  # 专辑描述
        ".track-description",  # 音轨描述
        ".game-description",  # 游戏描述
        # === HTML5语义化标签 ===
        "article",  # HTML5文章标签
        "main",  # HTML5主内容标签
        "section",  # HTML5节段标签
        # === 通用类名（模糊匹配） ===
        "[class*='article']",  # 包含"article"的类名
        "[class*='content']",  # 包含"content"的类名
        "[class*='post']",  # 包含"post"的类名
        "[class*='story']",  # 包含"story"的类名
        "[class*='body']",  # 包含"body"的类名
        "[class*='text']",  # 包含"text"的类名
        "[class*='main']",  # 包含"main"的类名
        "[class*='primary']",  # 包含"primary"的类名
        "[class*='detail']",  # 包含"detail"的类名
        # === ID选择器 ===
        "#content",  # 通用内容ID
        "#main-content",  # 主内容ID
        "#article-content",  # 文章内容ID
        "#post-content",  # 文章内容ID
        "#story-content",  # 故事内容ID
        "#main",  # 主要区域ID
        "#primary",  # 主要内容ID
        "#article-body",  # 文章主体ID
        "#content-area",  # 内容区域ID
        "#page-content",  # 页面内容ID
        # === 特殊网站 ===
        ".ztext",  # 知乎（旧版）
        ".RichText-inner",  # 知乎富文本
        ".highlight",  # 代码高亮（GitHub等）
        ".gist-file",  # GitHub Gist
        ".readme",  # GitHub README
        ".wiki-content",  # Wiki页面
        ".mw-parser-output",  # MediaWiki（维基百科）
        ".printfriendly",  # 打印友好版本
        ".reader-content",  # 阅读模式内容
        # === 回退选择器 ===
        ".main",  # 通用主内容类
        "body",  # 最后的回退选择器
    ]

    # 第三步：尝试找到正文容器
    for selector in content_selectors:
        content_elem = page_soup.select_one(selector)
        if content_elem:
            # 提取原始标签，添加去重和噪声过滤
            text_parts = []
            seen_texts = set()  # 用于去重
            for elem in content_elem.find_all(
                ["p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "span"]
            ):
                text = utils.clean_text(elem.get_text().strip())
                if text and len(text) > 10 and text not in seen_texts:  # 过滤过短文本并去重
                    # 过滤噪声关键词
                    if not any(keyword in text.lower() for keyword in noise_keywords):
                        text_parts.append(text)
                        seen_texts.add(text)

            if text_parts:
                # 保留段落结构，清理多余换行符
                full_text = "\n\n".join(text_parts)
                full_text = re.sub(r"\n{3,}", "\n\n", full_text).strip()
                if len(full_text) > min_abstract_len:
                    return full_text

    # 第四步：回退到 body
    body = page_soup.select_one("body")
    if body:
        for elem in body.select("nav, header, footer, aside, .ad, .advertisement, .sidebar, .menu"):
            elem.decompose()

        text_parts = []
        seen_texts = set()
        for elem in body.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "span"]):
            text = utils.clean_text(elem.get_text().strip())
            if text and len(text) > 10 and text not in seen_texts:
                if not any(keyword in text.lower() for keyword in noise_keywords):
                    text_parts.append(text)
                    seen_texts.add(text)

        if text_parts:
            full_text = "\n\n".join(text_parts)
            full_text = re.sub(r"\n{3,}", "\n\n", full_text).strip()
            if len(full_text) > min_abstract_len:
                return full_text

        # 第五步：极宽松回退，模仿原始版本
        text = utils.clean_text(body.get_text())
        if text and len(text) > min_abstract_len:
            return text

    return ""
