from dotenv import load_dotenv
load_dotenv()

from hello_agents import HelloAgentsLLM
from datetime import datetime
import json
import time

from codebasemaintainer import CodebaseMaintainer

def day_1_exploration(maintainer):
    response = maintainer.explore()
    print(f"\n助手总结:\n{response[:500]}...\n")

    response = maintainer.run("请查看 data_processor.py 文件，分析其代码设计")
    print(f"\n助手总结:\n{response[:500]}...\n")

    # 模拟时间流逝
    time.sleep(1)

def day_2_analysis(maintainer):
    response = maintainer.analyze()
    print(f"\n助手总结:\n{response[:500]}...\n")

    response = maintainer.run(
        "请分析 api_client.py 的代码质量，特别是错误处理部分，给出改进建议"
    )
    print(f"\n助手总结:\n{response[:500]}...\n")

    # 模拟时间流逝
    time.sleep(1)

def day_3_planning(maintainer):
    response = maintainer.plan_next_steps()
    print(f"\n助手总结:\n{response[:500]}...\n")

    response = maintainer.run(
        "请基于我们的分析，创建一个详细的本周重构计划。"
        "计划应该包括：目标、具体任务清单、时间安排和风险。"
        "请使用 NoteTool 创建一个 task_state 类型的笔记来记录这个计划。",
        mode = "plan"
    )
    print(f"\n助手总结:\n{response[:500]}...\n")

    # 模拟时间流逝
    time.sleep(1)

def week_later_review(maintainer):
    summary = maintainer.note_tool.run({"action": "summary"})
    print("📊 笔记摘要:")
    print(summary)

    report = maintainer.generate_report()
    print("\n📄 会话报告:")
    print(json.dumps(report, indent=2, ensure_ascii=False))

def main():
    maintainer = CodebaseMaintainer(
        project_name="demo_codebase",
        codebase_path="E:\\python workspace\\hello-agents\\code\\chapter9\\codebase",
        llm=HelloAgentsLLM(timeout=180)
    )

    # 执行三天工作流
    day_1_exploration(maintainer)
    day_2_analysis(maintainer)
    day_3_planning(maintainer)
    week_later_review(maintainer)

if __name__ == "__main__":
    main()