import re
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlencode
from .base_tool import LocalTool
from utils.response import ToolResponse
from utils.logger import global_logger

# Google 搜索相关导入
try:
    from googlesearch import search as google_search
except ImportError:
    google_search = None

# Crawl4AI 相关导入
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
except ImportError:
    AsyncWebCrawler = None


class GoogleSearchTool(LocalTool):
    """Google搜索工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "google_search"
        self.description = "执行Google搜索并返回结果"
    
    async def execute(self, task_id: str, workspace_path: Path, query: str, num_results: int = 50, **kwargs) -> ToolResponse:
        try:
            if google_search is None:
                return ToolResponse(
                    success=False, 
                    error="googlesearch-python not installed"
                )
            
            if not query:
                return ToolResponse(success=False, error="query is required")
            
            global_logger.info(f"Google 搜索: {query}, 结果数量: {num_results}")
            
            # 执行搜索
            results = []
            for res in google_search(query, num_results=num_results, advanced=True):
                results.append({
                    "title": getattr(res, "title", ""),
                    "url": getattr(res, "url", ""),
                    "description": getattr(res, "description", "")
                })
            
            return ToolResponse(
                success=True,
                data={
                    "query": query,
                    "results": results,
                    "total_results": len(results)
                }
            )
            
        except Exception as e:
            global_logger.error(f"Google 搜索错误: {str(e)}")
            return ToolResponse(success=False, error=str(e))


class CrawlPageTool(LocalTool):
    """网页爬取工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "crawl_page"
        self.description = "爬取指定URL的页面内容"
    
    async def execute(self, task_id: str, workspace_path: Path, url: str, output_dir: str = 'crawled_content', download_images: bool = False, **kwargs) -> ToolResponse:
        try:
            if AsyncWebCrawler is None:
                return ToolResponse(
                    success=False, 
                    error="crawl4ai not installed"
                )
            
            if not url:
                return ToolResponse(success=False, error="url is required")
            
            global_logger.info(f"爬取页面: {url}")
            
            # 构建输出目录
            task_path = self.get_task_path(task_id, workspace_path)
            full_output_dir = task_path / "upload" / output_dir
            full_output_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用 Crawl4AI 爬取页面
            async def _async_crawl():
                browser_conf = BrowserConfig(headless=True, verbose=False)
                run_conf = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
                async with AsyncWebCrawler(config=browser_conf) as crawler:
                    result = await crawler.arun(url, config=run_conf)
                    return result
            
            result = await _async_crawl()
            
            markdown_attr = getattr(result, "markdown", None)
            if markdown_attr is None:
                return ToolResponse(
                    success=False, 
                    error="无法从爬取结果中获取 Markdown"
                )
            
            markdown_text = (
                getattr(markdown_attr, "raw_markdown", None) or str(markdown_attr)
            )
            
            # 处理图片
            if download_images:
                images_dir = full_output_dir / "images"
                images_dir.mkdir(exist_ok=True)
                
                def _download_image(img_url: str) -> str:
                    """下载图片并返回本地路径"""
                    try:
                        import requests
                        resp = requests.get(img_url, timeout=15)
                        resp.raise_for_status()
                        
                        # 检查是否为图片
                        if not resp.headers.get("content-type", "").startswith("image"):
                            return img_url
                        
                        # 生成文件名
                        filename = os.path.basename(urlparse(img_url).path) or "image"
                        if "." not in filename:
                            mime_ext = resp.headers.get("content-type", "image/png").split("/")[-1]
                            filename = f"{filename}.{mime_ext}"
                        
                        local_path = images_dir / filename
                        counter = 1
                        while local_path.exists():
                            stem = local_path.stem
                            suffix = local_path.suffix
                            local_path = images_dir / f"{stem}_{counter}{suffix}"
                            counter += 1
                        
                        local_path.write_bytes(resp.content)
                        return str(local_path.relative_to(full_output_dir))
                        
                    except Exception as e:
                        global_logger.warning(f"图片下载失败: {img_url} -> {e}")
                        return img_url
                
                # 替换图片链接
                def _replace_image(match):
                    img_url = match.group(1)
                    local_path = _download_image(img_url)
                    return match.group(0).replace(img_url, local_path)
                
                markdown_text = re.sub(r"!\[[^\]]*\]\(([^\)]+)\)", _replace_image, markdown_text)
            else:
                # 移除图片标记
                markdown_text = re.sub(r"!\[[^\]]*\]\([^\)]+\)", "", markdown_text)
            
            # 保存 Markdown 文件
            md_path = full_output_dir / "content.md"
            md_path.write_text(markdown_text, encoding="utf-8")
            
            return ToolResponse(
                success=True,
                data={
                    "url": url,
                    "output_dir": str(full_output_dir.relative_to(task_path)),
                    "markdown_file": str(md_path.relative_to(task_path)),
                    "download_images": download_images,
                    "images_dir": str((full_output_dir / "images").relative_to(task_path)) if download_images else None
                }
            )
            
        except Exception as e:
            global_logger.error(f"页面爬取错误: {str(e)}")
            return ToolResponse(success=False, error=str(e))


class GoogleScholarSearchTool(LocalTool):
    """Google Scholar搜索工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "google_scholar_search"
        self.description = "搜索Google Scholar并保存结果"
    
    async def execute(self, task_id: str, workspace_path: Path, query: str, output_dir: str = 'scholar_results', year_low: int = None, year_high: int = None, pages: int = 1, **kwargs) -> ToolResponse:
        try:
            if AsyncWebCrawler is None:
                return ToolResponse(
                    success=False, 
                    error="crawl4ai not installed"
                )
            
            if not query:
                return ToolResponse(success=False, error="query is required")
            
            global_logger.info(f"Google Scholar 搜索: {query}, 页数: {pages}")
            
            # 构建输出目录
            task_path = self.get_task_path(task_id, workspace_path)
            full_output_dir = task_path / "upload" / output_dir
            full_output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成安全的文件名
            safe_query = re.sub(r'[^\w\s-]', '', query).strip()
            safe_query = re.sub(r'[-\s]+', '_', safe_query)
            
            base_url = "https://scholar.google.com/scholar"
            all_content = []
            
            async def _crawl_scholar_page(url: str) -> str:
                """爬取单个 Scholar 页面"""
                browser_conf = BrowserConfig(headless=True, verbose=False)
                run_conf = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
                async with AsyncWebCrawler(config=browser_conf) as crawler:
                    result = await crawler.arun(url, config=run_conf)
                    
                    markdown_attr = getattr(result, "markdown", None)
                    if markdown_attr is None:
                        return ""
                    
                    markdown_text = (
                        getattr(markdown_attr, "raw_markdown", None) or str(markdown_attr)
                    )
                    
                    # 移除图片标记
                    markdown_text = re.sub(r"!\[[^\]]*\]\([^\)]+\)", "", markdown_text)
                    return markdown_text
            
            # 爬取多页结果
            for page in range(pages):
                start = page * 10
                
                params = {
                    "start": str(start),
                    "q": query,
                    "as_sdt": "0,5"
                }
                
                if year_low:
                    params["as_ylo"] = str(year_low)
                if year_high:
                    params["as_yhi"] = str(year_high)
                
                url = f"{base_url}?{urlencode(params)}"
                global_logger.info(f"爬取 Google Scholar 第 {page + 1} 页")
                
                page_content = await _crawl_scholar_page(url)
                if page_content:
                    all_content.append(f"# 第 {page + 1} 页结果\n\n{page_content}")
            
            # 合并所有内容
            if all_content:
                final_content = f"# Google Scholar 搜索结果: {query}\n\n" + "\n\n---\n\n".join(all_content)
                
                # 生成文件名
                filename = f"{safe_query}"
                if year_low or year_high:
                    year_range = f"_{year_low or 'start'}-{year_high or 'end'}"
                    filename += year_range
                filename += ".md"
                
                md_path = full_output_dir / filename
                md_path.write_text(final_content, encoding="utf-8")
                
                return ToolResponse(
                    success=True,
                    data={
                        "query": query,
                        "pages": pages,
                        "year_low": year_low,
                        "year_high": year_high,
                        "output_dir": str(full_output_dir.relative_to(task_path)),
                        "markdown_file": str(md_path.relative_to(task_path)),
                        "filename": filename
                    }
                )
            else:
                return ToolResponse(
                    success=False,
                    error="未获取到任何 Scholar 搜索结果"
                )
            
        except Exception as e:
            global_logger.error(f"Google Scholar 搜索错误: {str(e)}")
            return ToolResponse(success=False, error=str(e)) 