"""测试天气查询 MCP 服务器"""
import asyncio
import json 
import os
import sys

#sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'HelloAgents'))
from hello_agents.protocols import MCPClient

async def test_weather_server():
    server_script = os.path.join(os.path.dirname(__file__), "mcp_weather_server.py")
    client = MCPClient(["python", server_script],keep_alive=False)
    try:
        async with client:
            # 测试1: 获取服务器信息
            info = json.loads(await client.call_tool("get_server_info", {}))
            print(f"服务器: {info["name"]} v{info['version']}")

            # 测试2: 列出支持的城市
            cities = json.loads(await client.call_tool("list_supported_cities", {}))
            print(f"支持城市: {cities['count']} 个")

            # 测试3: 查询北京天气
            weather = json.loads(await client.call_tool("get_weather", {"city":"北京"}))
            if "error" not in weather:
                print(f"\n北京天气: {weather['temperature']}°C, {weather['condition']}")
            else:
                print(f"❌ 天气查询失败：{weather['error']}")

            # 测试4: 查询深圳天气
            weather = json.loads(await client.call_tool("get_weather", {"city":"深圳"}))
            if "error" not in weather:
                print(f"深圳天气: {weather['temperature']}°C, {weather['condition']}")
            else:
                print(f"❌ 天气查询失败：{weather['error']}")

            print(f"\n✅ 所有测试完成！")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ =="__main__":
    asyncio.run(test_weather_server())