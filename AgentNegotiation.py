from hello_agents.protocols import A2AServer, A2AClient
import threading
import time

# 创建两个需要协商的Agent
agent1 = A2AServer(
    name="agent1",
    description="Agent 1"
)

@agent1.skill("propose")
def handle_proposal(text:str)->str:
    """处理协商提案"""
    import re

    # 解析提案
    match = re.match(r'propose\s+(.+)', text, re.IGNORECASE)
    proposal_str = match.group(1).strip() if match else text
    try:
        from ast import literal_eval
        proposal = literal_eval(proposal_str)
        task = proposal.get("task")
        deadline = proposal.get("deadline")

        # 评估提案
        if deadline >=7:# 至少需要7天
            result = {"accept":True, "message":"接受提案"}
        else:
            result={
                "accepted": False,
                "message": "时间太紧",
                "counter_proposal":{"deadline":7}
            }
        return str(result)
    except:
        return str({"accept":False, "message":"无效的提案格式"})

agent2 = A2AServer(
    name="agent2",
    description="Agent 2"
)

@agent2.skill("negotiate")
def negotiate_task(text: str) -> str:
    """发起协商"""
    import re

    # 解析任务和截止日期
    match = re.match(r'negotiate\s+task:(.+?)\s+deadline:(\d+)', text, re.IGNORECASE)
    if match:
        task = match.group(1).strip()
        deadline = int(match.group(2))

        # 向agent1发送提案
        proposal = {"task":task, "deadline":deadline}
        client = A2AClient("http://localhost:7000")
        response = client.execute_skill(
            "propose",
            f"propose {proposal}"
        )
        return response.get("result", str(response))

    else:
        return str({"status": "error", "message": "无效的协商请求"})

# 启动服务
threading.Thread(target=lambda: agent1.run(port=7000), daemon=True).start()
threading.Thread(target=lambda: agent2.run(port=7001), daemon=True).start()
time.sleep(2)

client = A2AClient("http://localhost:7001")
result = client.execute_skill(
    "negotiate",
    "negotiate task:写报告 deadline:3"
)
print(result)