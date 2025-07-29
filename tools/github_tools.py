import requests
import os
from typing import Dict, Any, List, Optional
from .base_tool import LocalTool
from utils.response import ToolResponse
from utils.logger import global_logger


class GitHubSearchTool(LocalTool):
    """GitHub 搜索工具集（主机端运行）"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "github_search_repositories"
        self.description = "搜索GitHub仓库"
        self.base_url = "https://api.github.com"
    
    def _get_github_token(self, token: Optional[str] = None) -> str:
        """获取 GitHub Token"""
        if token:
            return token
        
        # 从环境变量获取
        env_token = os.getenv('GITHUB_TOKEN')
        if env_token:
            return env_token
        
        raise ValueError("GitHub Token is required. Please provide token parameter or set GITHUB_TOKEN environment variable.")
    
    def _get_headers(self, token: str) -> Dict[str, str]:
        """获取请求头"""
        return {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    async def execute(self, task_id: str, workspace_path, query: str, 
                                       sort: str = 'stars', order: str = 'desc',
                                       per_page: int = 10, page: int = 1,
                     token: Optional[str] = None, **kwargs) -> ToolResponse:
        """搜索 GitHub 仓库（仅基于仓库名称）
        
        Args:
            task_id: 任务ID
            query: 搜索关键词（将只在仓库名称中搜索）
            sort: 排序依据（stars, forks, updated）
            order: 排序顺序（asc, desc）
            per_page: 每页结果数（最大100）
            page: 页码（从1开始）
            token: GitHub Token（可选，如果未提供则从环境变量获取）
        
        Returns:
            ToolResponse: 包含搜索结果的响应
        """
        try:
            # 获取 GitHub Token
            github_token = self._get_github_token(token)
            headers = self._get_headers(github_token)
            
            # 构建搜索URL - 添加 in:name 限定符，只搜索仓库名称
            search_url = f"{self.base_url}/search/repositories"
            search_query = f"{query} in:name"  # 限制只搜索仓库名称
            params = {
                'q': search_query,
                'sort': sort,
                'order': order,
                'per_page': min(per_page, 100),  # GitHub API 限制最大100
                'page': page
            }
            
            global_logger.info(f"Searching GitHub repositories with query: '{query}'")
            
            # 发送请求
            response = requests.get(search_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                repositories = data.get('items', [])
                
                # 格式化结果
                formatted_repos = []
                for repo in repositories:
                    formatted_repo = {
                        'name': repo.get('name', ''),
                        'full_name': repo.get('full_name', ''),
                        'description': repo.get('description', ''),
                        'html_url': repo.get('html_url', ''),
                        'clone_url': repo.get('clone_url', ''),
                        'ssh_url': repo.get('ssh_url', ''),
                        'stars': repo.get('stargazers_count', 0),
                        'forks': repo.get('forks_count', 0),
                        'watchers': repo.get('watchers_count', 0),
                        'language': repo.get('language', ''),
                        'created_at': repo.get('created_at', ''),
                        'updated_at': repo.get('updated_at', ''),
                        'pushed_at': repo.get('pushed_at', ''),
                        'size': repo.get('size', 0),
                        'default_branch': repo.get('default_branch', ''),
                        'owner': {
                            'login': repo.get('owner', {}).get('login', ''),
                            'avatar_url': repo.get('owner', {}).get('avatar_url', ''),
                            'html_url': repo.get('owner', {}).get('html_url', '')
                        },
                        'license': repo.get('license', {}).get('name', '') if repo.get('license') else '',
                        'topics': repo.get('topics', []),
                        'archived': repo.get('archived', False),
                        'disabled': repo.get('disabled', False),
                        'private': repo.get('private', False)
                    }
                    formatted_repos.append(formatted_repo)
                
                result_data = {
                    'total_count': data.get('total_count', 0),
                    'incomplete_results': data.get('incomplete_results', False),
                    'current_page': page,
                    'per_page': per_page,
                    'query': query,
                    'sort': sort,
                    'order': order,
                    'repositories': formatted_repos
                }
                
                global_logger.info(f"Found {len(formatted_repos)} repositories (total: {result_data['total_count']})")
                
                return ToolResponse(
                    success=True,
                    data=result_data
                )
                
            elif response.status_code == 403:
                error_msg = "GitHub API rate limit exceeded or authentication failed"
                if 'rate limit' in response.text.lower():
                    error_msg = "GitHub API rate limit exceeded. Please wait or use a different token."
                elif 'authentication' in response.text.lower():
                    error_msg = "GitHub authentication failed. Please check your token."
                
                global_logger.error(f"GitHub API error: {error_msg}")
                return ToolResponse(
                    success=False,
                    error=error_msg
                )
                
            elif response.status_code == 422:
                error_msg = f"Invalid search query: {query}"
                global_logger.error(f"GitHub API error: {error_msg}")
                return ToolResponse(
                    success=False,
                    error=error_msg
                )
                
            else:
                error_msg = f"GitHub API error: {response.status_code} - {response.text}"
                global_logger.error(error_msg)
                return ToolResponse(
                    success=False,
                    error=error_msg
                )
                
        except requests.exceptions.Timeout:
            error_msg = "GitHub API request timeout"
            global_logger.error(error_msg)
            return ToolResponse(success=False, error=error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"GitHub API request failed: {str(e)}"
            global_logger.error(error_msg)
            return ToolResponse(success=False, error=error_msg)
            
        except Exception as e:
            error_msg = f"GitHub search error: {str(e)}"
            global_logger.error(error_msg)
            return ToolResponse(success=False, error=error_msg)
    

class GitHubRepoInfoTool(LocalTool):
    """GitHub仓库信息获取工具"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "github_get_repository_info"
        self.description = "获取GitHub仓库详细信息"
        self.base_url = "https://api.github.com"
    
    def _get_github_token(self, token: Optional[str] = None) -> str:
        """获取 GitHub Token"""
        if token:
            return token
        
        # 从环境变量获取
        env_token = os.getenv('GITHUB_TOKEN')
        if env_token:
            return env_token
        
        raise ValueError("GitHub Token is required. Please provide token parameter or set GITHUB_TOKEN environment variable.")
    
    def _get_headers(self, token: str) -> Dict[str, str]:
        """获取请求头"""
        return {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    async def execute(self, task_id: str, workspace_path, full_name: str,
                     token: Optional[str] = None, **kwargs) -> ToolResponse:
        """获取指定仓库的详细信息
        
        Args:
            task_id: 任务ID
            full_name: 仓库全名（如 "owner/repo"）
            token: GitHub Token（可选）
        
        Returns:
            ToolResponse: 包含仓库详细信息的响应
        """
        try:
            # 获取 GitHub Token
            github_token = self._get_github_token(token)
            headers = self._get_headers(github_token)
            
            # 构建API URL
            api_url = f"{self.base_url}/repos/{full_name}"
            
            global_logger.info(f"Getting repository info for: {full_name}")
            
            # 发送请求
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                repo = response.json()
                
                # 格式化结果
                repo_info = {
                    'name': repo.get('name', ''),
                    'full_name': repo.get('full_name', ''),
                    'description': repo.get('description', ''),
                    'html_url': repo.get('html_url', ''),
                    'clone_url': repo.get('clone_url', ''),
                    'ssh_url': repo.get('ssh_url', ''),
                    'stars': repo.get('stargazers_count', 0),
                    'forks': repo.get('forks_count', 0),
                    'watchers': repo.get('watchers_count', 0),
                    'language': repo.get('language', ''),
                    'created_at': repo.get('created_at', ''),
                    'updated_at': repo.get('updated_at', ''),
                    'pushed_at': repo.get('pushed_at', ''),
                    'size': repo.get('size', 0),
                    'default_branch': repo.get('default_branch', ''),
                    'owner': {
                        'login': repo.get('owner', {}).get('login', ''),
                        'avatar_url': repo.get('owner', {}).get('avatar_url', ''),
                        'html_url': repo.get('owner', {}).get('html_url', '')
                    },
                    'license': repo.get('license', {}).get('name', '') if repo.get('license') else '',
                    'topics': repo.get('topics', []),
                    'archived': repo.get('archived', False),
                    'disabled': repo.get('disabled', False),
                    'private': repo.get('private', False),
                    'homepage': repo.get('homepage', ''),
                    'has_issues': repo.get('has_issues', False),
                    'has_projects': repo.get('has_projects', False),
                    'has_wiki': repo.get('has_wiki', False),
                    'has_pages': repo.get('has_pages', False),
                    'open_issues_count': repo.get('open_issues_count', 0),
                    'network_count': repo.get('network_count', 0),
                    'subscribers_count': repo.get('subscribers_count', 0)
                }
                
                global_logger.info(f"Retrieved info for repository: {full_name}")
                
                return ToolResponse(
                    success=True,
                    data=repo_info
                )
                
            elif response.status_code == 404:
                error_msg = f"Repository not found: {full_name}"
                global_logger.error(error_msg)
                return ToolResponse(success=False, error=error_msg)
                
            else:
                error_msg = f"GitHub API error: {response.status_code} - {response.text}"
                global_logger.error(error_msg)
                return ToolResponse(success=False, error=error_msg)
                
        except Exception as e:
            error_msg = f"GitHub repository info error: {str(e)}"
            global_logger.error(error_msg)
            return ToolResponse(success=False, error=error_msg) 