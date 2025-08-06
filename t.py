import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote
from src.aiforge.core.runner import AIForgeRunner


def search_web(search_query, max_results):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def extract_content(url):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, "html.parser")

            meta_date = soup.find(
                "meta",
                property=["article:published_time", "datePublished", "pubdate", "publishdate"],
            )
            if meta_date:
                date = meta_date.get("content", "")
            else:
                time_tag = soup.find("time")
                if time_tag:
                    date = time_tag.get("datetime", time_tag.text)
                else:
                    date = ""

            content = " ".join([p.get_text().strip() for p in soup.find_all("p")])
            content = re.sub(r"\s+", " ", content).strip()
            if len(content) < 75:
                content = soup.get_text()
                content = re.sub(r"\s+", " ", content).strip()

            return content, date
        except Exception:
            return None, None

    def search_baidu(query, max_results):
        url = f"https://www.baidu.com/s?wd={quote(query)}&rn={max_results}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            for item in soup.select(".result.c-container")[:max_results]:
                link = item.find("a")["href"]
                title = item.find("h3").get_text()
                content, date = extract_content(link)
                if content:
                    results.append(
                        {"title": title, "content": content[:500], "source": link, "date": date}
                    )
            return results
        except Exception:
            return []

    def search_bing(query, max_results):
        url = f"https://www.bing.com/search?q={quote(query)}&count={max_results}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            for item in soup.select(".b_algo")[:max_results]:
                link = item.find("a")["href"]
                title = item.find("h2").get_text()
                content, date = extract_content(link)
                if content:
                    results.append(
                        {"title": title, "content": content[:500], "source": link, "date": date}
                    )
            return results
        except Exception:
            return []

    results = []
    results.extend(search_baidu(search_query, max_results))
    results.extend(search_bing(search_query, max_results))

    results = [r for r in results if r["content"] and len(r["content"]) >= 75]

    return {
        "data": results,
        "status": "success",
        "summary": "搜索完成",
        "metadata": {
            "timestamp": time.time(),
            "task_type": "data_fetch",
            "search_query": search_query,
            "execution_type": "free_form_search",
        },
    }


if __name__ == "__main__":
    # 创建沙盒运行器
    security_config = {
        "execution_timeout": 30,
        "memory_limit_mb": 512,
        "network": {
            "disable_network_validation": False,
            "block_network_access": False,
            "block_network_modules": False,
            "restrict_network_access": False,
            "enable_domain_filtering": True,
        },
    }

    runner = AIForgeRunner("test_workdir", security_config)

    # 将完整的函数代码作为字符串传入沙盒
    test_code = """  
import os    
import requests    
from bs4 import BeautifulSoup    
import re    
import time    
from urllib.parse import quote    

def search_web(search_query, max_results):  
    headers = {  
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"  
    }  
  
    def extract_content(url):  
        try:  
            response = requests.get(url, headers=headers, timeout=10)  
            response.encoding = response.apparent_encoding  
            soup = BeautifulSoup(response.text, "html.parser")  
              
            content = " ".join([p.get_text().strip() for p in soup.find_all("p")])  
            content = re.sub(r"\\\\s+", " ", content).strip()  
            if len(content) < 75:  
                content = soup.get_text()  
                content = re.sub(r"\\\\s+", " ", content).strip()  
              
            return content, ""  
        except Exception as e:  
            print(f"提取内容失败: {e}")  
            return None, None  
  
    def search_baidu(query, max_results):  
        url = f"https://www.baidu.com/s?wd={quote(query)}&rn={max_results}"  
        try:  
            response = requests.get(url, headers=headers, timeout=10)  
            print(f"百度搜索状态码: {response.status_code}")  
            soup = BeautifulSoup(response.text, "html.parser")  
            results = []  
            for item in soup.select(".result.c-container")[:max_results]:  
                try:  
                    link = item.find("a")["href"]  
                    title = item.find("h3").get_text()  
                    content, date = extract_content(link)  
                    if content:  
                        results.append({  
                            "title": title,   
                            "content": content[:500],   
                            "source": link,   
                            "date": date  
                        })  
                except Exception as e:  
                    print(f"处理搜索结果失败: {e}")  
                    continue  
            return results  
        except Exception as e:  
            print(f"百度搜索失败: {e}")  
            return []  
  
    results = []  
    results.extend(search_baidu(search_query, max_results))  
      
    print(f"找到 {len(results)} 个结果")  
      
    return {  
        "data": results,  
        "status": "success",  
        "summary": "搜索完成",  
        "metadata": {  
            "timestamp": time.time(),  
            "task_type": "data_fetch",  
            "search_query": search_query,  
            "execution_type": "free_form_search",  
        },  
    }  
  
# 执行搜索并包含调试信息  
search_result = search_web("名古屋市市长 南京 恢复交流", 10)  
__result__ = search_result
"""

    # 在沙盒中执行
    result = runner.execute_code(test_code)
    print("沙盒执行结果:", result)
