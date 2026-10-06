from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.context import ContextBuilder, ContextConfig, ContextPacket
from hello_agents.tools import MemoryTool,RAGTool, NoteTool
from datetime import datetime
from typing import List, Dict
import re

class ProjectAssistant(SimpleAgent):
    """长期项目助手,集成 NoteTool 和 ContextBuilder"""

    def __init__(self, name: str, project_name:str, **kwargs):
        super().__init__(name=name, llm=HelloAgentsLLM(), **kwargs)

        self.project_name = project_name

        # 初始化工具
        self.memory_tool = MemoryTool(user_id=project_name)
        self.rag_tool = RAGTool(knowledge_base_path=f"./{project_name}_kb")
        self.note_tool = NoteTool(workspace=f"./{project_name}_notes")

        # 初始化上下文构建器
        self.context_builder = ContextBuilder(
            memory_tool=self.memory_tool,
            rag_tool=self.rag_tool if self.rag_tool.initialized else None,
            # 学习示例暂时关闭相关性门槛，避免 0.2.8 的空格切词过滤中文。
            # Token 预算仍然生效；正式使用时应改进中文相关性计算。
            config=ContextConfig(max_tokens=4000, min_relevance=0.0)
        )

        self.conversation_history = []

    def run(self, user_input:str, note_as_action:bool = False)->str:
        """运行助手,自动集成笔记"""

        # 1. 从 NoteTool 检索相关笔记
        relevant_notes = self._retrieve_relevant_notes(user_input)

        # 2. 将笔记转换为 ContextPacket
        note_packets = self._notes_to_packets(relevant_notes)
        print(
            f"[ContextBuilder] 候选笔记 {len(note_packets)} 条，"
            f"历史消息 {len(self.conversation_history)} 条"
        )

        # 3. 构建优化的上下文
        context = self.context_builder.build(
            user_query=user_input,
            conversation_history=self.conversation_history,
            system_instructions = self._build_system_instructions(),
            additional_packets = note_packets
        )

        # 4. 使用优化后的上下文调用 LLM
        messages = [
            {"role":"system", "content": context},
            {"role":"user", "content":user_input}
        ]

        # 5. 调用 LLM
        response = self.llm.invoke(messages)

        # 6. 如果需要,将交互记录为笔记
        if note_as_action:
            self._save_as_note(user_input, response)

        # 7. 更新对话历史
        self._update_history(user_input, response)

        return response

    def _retrieve_relevant_notes(self, query: str, limit: int = 3)->List[Dict]:
        """检索相关笔记"""
        if limit <= 0:
            return []

        try:
            # 0.2.8 的 list/search 返回展示文本，不能直接当字典列表处理。
            # 从本地索引取近期 blocker/action，避免整句搜索遗漏项目进展。
            recent_notes = sorted(
                self.note_tool.notes_index["notes"],
                key=lambda note: note.get("updated_at", note.get("created_at", "")),
                reverse=True
            )
            blocker_ids = [
                note["id"] for note in recent_notes if note["type"] == "blocker"
            ][:2]
            action_ids = [
                note["id"] for note in recent_notes if note["type"] == "action"
            ][:2]

            # 通用搜索
            search_results = self.note_tool.run({
                "action":"search",
                "query":query,
                "limit":limit
            })

            search_ids = re.findall(
                r"(?m)^\s*ID:\s*(note_[A-Za-z0-9_-]+)",
                search_results
            )
            # 优先阻塞项，其次搜索结果，最后用近期行动计划补充背景。
            note_ids = list(dict.fromkeys(blocker_ids + search_ids + action_ids))

            notes = []

            for note_id in note_ids:
                note_path = self.note_tool.workspace / f"{note_id}.md"

                if not note_path.exists():
                    continue

                try:
                    note = self.note_tool._markdown_to_note(
                        note_path.read_text(encoding="utf-8")
                    )
                except (OSError, ValueError) as e:
                    print(f"[WARNING] 跳过无法读取的笔记 {note_id}: {e}")
                    continue

                note["note_id"] = note["id"]
                notes.append(note)

                if len(notes) >= limit:
                    break

            return notes
        except Exception as e:
            print(f"[WARNING] 笔记检索失败: {e}")
            return []

    def _notes_to_packets(self, notes: List[Dict])->List[ContextPacket]:
        """将笔记转换为上下文包"""
        packets = []

        for note in notes:
            content = f"[笔记:{note['title']} | ID:{note['note_id']}]\n{note['content']}"

            packets.append(ContextPacket(
                content=content,
                timestamp=datetime.fromisoformat(note['updated_at']),
                # 交给 ContextPacket 计算实际 Token 数，避免低估中文长度。
                relevance_score=0.75,
                metadata={
                    "type":"retrieval",
                    "note_type":note["type"],
                    "note_id":note["note_id"]
                }
            ))

        return packets

    def _save_as_note(self, user_input:str, response:str):
        """将交互保存为笔记"""
        try:
            # 判断应该保存为什么类型的笔记
            if "问题" in user_input or "阻塞" in user_input:
                note_type = "blocker"
            elif "计划" in user_input or "下一步" in user_input:
                note_type = "action"
            else:
                note_type = "conclusion"

            result = self.note_tool.run({
                "action":"create",
                "title":f"{user_input[:30]}...",
                "content":f"## 问题\n{user_input}\n\n## 分析\n{response}",
                "note_type":note_type,
                "tags":[self.project_name, "auto_generated"]
            })
            if result.startswith("✅"):
                print(f"[NoteTool] 已保存 {note_type} 笔记")
            else:
                print(f"[WARNING] 保存笔记失败: {result}")
        except Exception as e:
            print(f"[WARNING] 保存笔记失败: {e}")

    def _build_system_instructions(self)->str:
        """构建系统指令"""
        return f"""你是 {self.project_name} 项目的长期助手。

你的职责:
1. 基于历史笔记提供连贯的建议
2. 追踪项目进展和待解决问题
3. 在回答时引用相关的历史笔记
4. 提供具体、可操作的下一步建议

注意:
- 优先关注标记为 blocker 的问题
- 在建议中说明依据来源(笔记、记忆或知识库)
- 保持对项目整体进度的认识"""

    def _update_history(self, user_input:str, response:str):
        """更新对话历史"""
        from hello_agents.core.message import Message
        self.conversation_history.append(Message(content=user_input, role="user", timestamp = datetime.now()))

        self.conversation_history.append(Message(content=response, role="assistant", timestamp = datetime.now()))

        # 限制历史长度
        if len(self.conversation_history) >10:
            self.conversation_history = self.conversation_history[-10:]

def main():
    assistant = ProjectAssistant(
        name="项目助手",
        project_name="data_pipeline_refactoring"
    )

    # 第一次交互：保存项目进展和下一步行动，并展示回答。
    response = assistant.run(
        "我们已经完成了数据模型层的重构,测试覆盖率达到85%。下一步计划重构业务逻辑层。",
        note_as_action=True
    )
    print("\n✅ 助手回答（项目进展）：")
    print(response)

    # 第二次交互：保存阻塞问题，并展示基于历史信息生成的建议。
    response = assistant.run(
        "在重构业务逻辑层时,我遇到了依赖版本冲突的问题,该如何解决?",
        note_as_action=True
    )
    print("\n✅ 助手回答（依赖冲突）：")
    print(response)

    # 摘要会包含以前运行保存的笔记，不会自动清空。
    summary = assistant.note_tool.run({"action":"summary"})
    print("\n" + summary)


if __name__ == "__main__":
    main()
