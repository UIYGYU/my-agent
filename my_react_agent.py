MY_REACT_PROMPT = """你是一个具备推理和行动能力的AI助手。你可以通过思考分析问题，然后调用合适的工具来获取信息，最终给出准确的答案。

## 可用工具
{tools}

## 工作流程
请严格按照以下格式进行回应，每次只能执行一个步骤:

Thought: 分析当前问题，思考需要什么信息或采取什么行动。
Action: 选择一个行动，格式必须是以下之一:
- `{{tool_name}}[{{tool_input}}]` - 调用指定工具
- `Finish[最终答案]` - 当你有足够信息给出最终答案时

## 重要提醒
1. 每次回应必须包含Thought和Action两部分
2. 工具调用的格式必须严格遵循:工具名[参数]
3. 只有当你确信有足够信息回答问题时，才使用Finish
4. 如果工具返回的信息不够，继续使用其他工具或相同工具的不同参数

## 当前任务
**Question:** {question}

## 执行历史
{history}

现在开始你的推理和行动:
"""
import re
from typing import Optional,List,Tuple, Any, Union
from hello_agents import ReActAgent,HelloAgentsLLM,Config,Message,ToolRegistry
class MyReactAgent(ReActAgent):
    """
    重写的ReAct Agent - 推理与行动结合的智能体
    """

    def __init__(
            self,
            name:str,
            llm:HelloAgentsLLM,
            tool_registry:ToolRegistry,
            system_prompt:Optional[str]=None,
            config:Optional[Config]=None,
            max_steps:int=5,
            custom_prompt:Optional[str]=None
    ):
        super().__init__(name, llm, system_prompt, config)
        self.tool_registry=tool_registry
        self.max_steps=max_steps
        self.current_history:List[str]=[]
        self.prompt_template = custom_prompt if custom_prompt else MY_REACT_PROMPT
        print(f"✅ {name} 初始化完成，最大步数: {max_steps}")

    def run(self, input_text: str, **kwargs)->str:
        """运行ReAct Agent"""
        self.current_history=[]
        current_step=0

        print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

        while current_step<self.max_steps:
            current_step+=1
            print(f"\n--- 第 {current_step} 步 ---")

            # 1. 构建提示词
            tool_desc=self.tool_registry.get_tools_description()
            history_str="\n".join(self.current_history)
            prompt = self.prompt_template(
                tools=tool_desc,
                question=input_text,
                history=history_str
            )

            # 2. 调用LLM
            message=[{"role":"user","conternt":prompt}]
            response_text = self.llm.invoke(messages=message, **kwargs)

            # 3. 解析输出
            thought, action = self._parse_output(response_text)

            # 4. 检查完成条件
            if action and action.startswith("Finish"):
                final_answer = self._parse_action_input(action_text=action)
                self.add_message(Message(input_text, "user"))
                self.add_message(Message(final_answer,"assistant"))
                return final_answer

            # 5. 执行工具调用
            if action:
                tool_name, tool_input = self._parse_action(action_text=action)
                observation = self.tool_registry.execute_tool(tool_name, tool_input)
                self.current_history.append(f"Action:{action}")
                self.current_history.append(f"Observation:{observation}")

        # 达到最大步数
        final_answer = "抱歉，我无法在限定步数内完成这个任务。"
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_answer, "assistant"))
        return final_answer

    def _invoke_with_tools(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], tool_choice: Union[str, dict], **kwargs):
        """调用底层OpenAI客户端执行函数调用"""
        client = getattr(self.llm, "_client",None)
        if client is None:
            raise RuntimeError("HelloAgentsLLM 未正确初始化客户端，无法执行函数调用。")

        client_kwargs = dict(kwargs)
        client_kwargs.setdefault("temperature", self.llm.temperature)
        if self.llm.max_tokens is not None:
            client_kwargs.setdefault("max_tokens", self.llm.max_tokens)

        return client.chat.completions.create(
            model=self.llm.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            **client_kwargs,
        )

#内部逻辑是对Openai 原生的functioncall作再封装
#OpenAI 原生functioncall示例
from openai import  OpenAI
client = OpenAI()

tools = [
  {
    "type": "function",
    "function": {
      "name": "get_current_weather",
      "description": "Get the current weather in a given location",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "The city and state, e.g. San Francisco, CA",
          },
          "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
        },
        "required": ["location"],
      },
    }
  }
]
messages = [{"role": "user", "content": "What's the weather like in Boston today?"}]
completion = client.chat.completions.create(
  model="gpt-5",
  messages=messages,
  tools=tools,
  tool_choice="auto"
)

print(completion)

from abc import ABC, abstractmethod
from openai import BaseModel
from typing import Callable, Dict
class Tool(ABC):
    """工具基类"""

    def __init__(self, name :str, description:str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters: Dict[str, Any])->str:
        """执行工具"""
        pass

    @abstractmethod
    def get_parameters(self)->List[ToolParameter]:
        """获取工具参数定义"""
        pass

    def to_openai_schema(self)->Dict[str, Any]:
        """转换为 OpenAI function calling schema 格式

        用于 FunctionCallAgent，使工具能够被 OpenAI 原生 function calling 使用

        Returns:
            符合 OpenAI function calling 标准的 schema
        """
        parameters = self.get_parameters()

        # 构建 properties
        properties = {}#dict
        required = []#list

        for param in parameters:
            # 基础属性定义
            prop={
                "type": param.type,
                "description":param.description
            }

            # 如果有默认值，添加到描述中（OpenAI schema 不支持 default 字段）
            if param.default is not None:
                prop["description"] = f"{param.description}(默认: {param.default})"

            # 如果是数组类型，添加 items 定义
            if param.type == "array":
                prop["items"] = {"type":"string"}# 默认字符串数组

            properties[param.name] = prop

            # 收集必需参数
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function":{
                "name": self.name,
                "description": self.description,
                "parameters":{
                    "type":"object",
                    "properties": properties,
                    "required":required
                }
            }
        }

class ToolParameter(BaseModel):
    """工具参数定义"""
    name:str
    type:str
    description:str
    required: bool = True
    default: Any = None

class ToolRegistry:
    """HelloAgents工具注册表"""

    def __init__(self):
        self._tools:dict[str, Tool] = {}
        self._functions:dict[str, dict[str, Any]] = {}

    def register_tool(self, tool:Tool):
        """注册Tool对象"""
        if tool.name in self._tools:
            print(f"⚠️ 警告:工具 '{tool.name}' 已存在，将被覆盖。")
        self._tools[tool.name]=tool
        print(f"✅ 工具 '{tool.name}' 已注册。")

    def register_function(self, name:str, description:str, func:Callable[[str],str]):
        """
        直接注册函数作为工具（简便方式）

        Args:
            name: 工具名称
            description: 工具描述
            func: 工具函数，接受字符串参数，返回字符串结果
        """
        if name in self._functions:
            print(f"⚠️ 警告:工具 '{name}' 已存在，将被覆盖。")

        self._functions[name]={
            "description":description,
            "func":func
        }

        print(f"✅ 工具 '{name}' 已注册。")

    def get_tools_description(self)->str:
        """获取所有可用工具的格式化描述字符串"""
        description=[]

        # Tool对象描述
        for tool in self._tools.values():
            description.append(f"- {tool.name}: {tool.description}")

        # 函数工具描述
        for name, info in self._functions.values():
            description.append(f"- {name}:{info['description']}")

        return "\n".join(description) if description else "暂无可用工具"