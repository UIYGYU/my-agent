# my_llm.py
import os
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel
from openai import OpenAI
from hello_agents import HelloAgentsLLM

class MyLLM(HelloAgentsLLM):
    """
    一个自定义的LLM客户端，通过继承增加了对ModelScope的支持。
    """
    def __init__(
            self,
            model: Optional[str] = None,
            api_key: str| None = None,
            base_url:Optional[str] = None,
            provider:Optional[str] = "auto",
            **kwargs
    ):
        # 检查provider是否为我们想处理的'modelscope'
        if provider == "modelscope":
            print("正在使用自定义的 ModelScope Provider")
            self.provider = "modelscope"

            #解析 ModelScope 的凭证
            self.api_key = api_key or os.getenv("MODELSCOPE_API_KEY")
            self.api_key = base_url or "https://api-inference.modelscope.cn/v1/"

            #验证凭证是否存在
            if not self.api_key:
                raise ValueError("ModelScope API key not found. Please set MODELSCOPE_API_KEY environment variable.")

            #设置默认模型和其他参数
            self.model = model or os.getenv("LLM_MODEL_ID") or "Qwen/Qwen2.5-VL-72B-Instruct"
            self.temperature = kwargs.get('temperature', 0.7)
            self.max_tokens = kwargs.get('max_tokens')
            self.timeout = kwargs.get('timeout', 60)

            # 使用获取的参数创建OpenAI客户端实例
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        else:
            # 如果不是 modelscope, 则完全使用父类的原始逻辑来处理
            super().__init__(model=model,api_key=api_key,base_url=base_url,provider=provider,**kwargs)

    def _auto_detect_provider(self, api_key : Optional[str], base_url: Optional[str])->str:
        """
        自动检测LLM提供商
        """
        # 1. 检查特定提供商的环境变量 (最高优先级)
        if os.getenv("MODELSCOPE_API_KEY"): return "modelscope"
        if os.getenv("OPENAI_API_KEY"): return "openai"
        if os.getenv("ZHIPU_API_KEY"): return "zhipu"
        # ... 其他服务商的环境变量检查

        # 获取通用的环境变量
        autual_api_key =api_key or os.getenv("LLM_API_KEY")
        autual_base_url = base_url or os.getenv("LLM_BASE_URL")

        # 2. 根据 base_url 判断
        if autual_base_url:
            base_url_lower = autual_base_url.lower()
            if "api-inference.modelscope.cn" in base_url_lower: return "modelscope"
            if "open.bigmodel.cn" in base_url_lower: return "zhipu"
            if "localhost" in base_url_lower or "127.0.0.1" in base_url_lower:
                if "11434" in base_url_lower: return "ollama"
                if "8000" in base_url_lower: return "vllm"
                return "local"# 其他本地端口

        # 3. 根据 API 密钥格式辅助判断
        if autual_api_key:
            if autual_api_key.startswith("ms-"):return "modelscope"
            # ... 其他密钥格式判断

        # 4. 默认返回 'auto'，使用通用配置
        #return "auto"
        return super()._auto_detect_provider(api_key, base_url)

    def _resolve_credentials(self, api_key: Optional[str], base_url: Optional[str])->tuple[str, str]:
        """根据provider解析API密钥和base_url"""
        if self.provider == "openai":
            resolved_api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or os.getenv("https://api.openai.com/v1")
            return resolved_api_key, resolved_base_url
        elif self.provider == "modelscope":
            resolved_api_key = api_key or os.getenv("MODELSCOPE_API_KEY") or os.getenv("LLM_API_KEY")
            resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or os.getenv("https://api-inference.modelscope.cn/v1/")
            return resolved_api_key, resolved_base_url
        return super()._resolve_credentials(api_key, base_url)

from dotenv import load_dotenv

load_dotenv()

# 实例化我们重写的客户端，并指定provider
llm = MyLLM(provider="modelscope")

#准备消息
messages = [{"role":"user", "content":"你好，请介绍一下你自己。"}]

# 发起调用，think等方法都已从父类继承，无需重写
response_stream = llm.think(messages=messages)

# 打印响应
print("ModelScope Response:")
for trunk in response_stream:
    # chunk在my_llm库中已经打印过一遍，这里只需要pass即可
    # print(chunk, end="", flush=True)
    pass

# 定义消息角色的类型，限制其取值
MessageRole = Literal["user", "assistant", "system", "tool"]

class Message(BaseModel):
    """消息类"""

    content: str
    role: MessageRole
    timestamp:datetime = None
    metadata: Optional[Dict[str, Any]] = None

    def __init__(self, content:str, role:MessageRole, **kwargs):
        super().__init__(
            content = content,
            role=role,
            timestamp=kwargs.get('timestamp', datetime.now()),
            metadata=kwargs.get('metadata', {})
        )

    def to_dict(self)->Dict[str,Any]:
        """转换为字典格式（OpenAI API格式）"""
        return{
            "role":self.role,
            "content":self.content
        }

    def __str__(self)->str:
        return f"[{self.role}]{self.content}"

class Config(BaseModel):
    """HelloAgents配置类"""

    # LLM配置
    default_model:str = "gpt-3.5-turbo"
    default_provider:str = "openai"
    temperature:float=0.7
    max_tokens:Optional[int]=None

    # 系统配置
    debug:bool=False
    log_level:str="INFO"

     # 其他配置
    max_history_length: int = 100

    def from_env(cls)->"Config":
        """从环境变量创建配置"""
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None
        )

    def to_dict(self)->Dict[str,Any]:
        """转换为字典"""
        return self.model_dump()

"""Agent基类"""
from abc import ABC, abstractmethod
class Agent(ABC):
    """Agent基类"""

    def __init__(self,
        name:str,
        llm:HelloAgentsLLM,
        system_prompt:Optional[str]=None,
        config:Optional[Config]=None
    ):
        self.name=name
        self.llm=llm
        self.system_prompt=system_prompt
        self.config = config or Config()
        self._history:list[Message]=[]

    @abstractmethod
    def run(self,input_text:str, **kwargs)->str:
        """运行Agent"""
        pass

    def add_message(self, message:Message):
        """添加消息到历史记录"""
        self._history.append(message)

    def clear_message(self):
        """清空历史记录"""
        self._history.clear()

    def get_history(self):
        """获取历史记录"""
        return self._history.copy()

    def __str__(self)->str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
        