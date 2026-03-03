"""
VeADK 聊天机器人运行示例
"""

import asyncio
from veadk import Runner
from chat_agent.agent import root_agent


async def main():
    """简单的聊天循环示例"""
    print("🤖 VeADK 聊天机器人已启动！")
    print("输入 'quit' 或 'exit' 退出\n")
    
    runner = Runner(agent=root_agent)
    
    while True:
        try:
            user_input = input("你: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("👋 再见！")
                break
            
            if not user_input:
                continue
            
            print("机器人: ", end="", flush=True)
            response = await runner.run(user_input)
            print(f"{response}\n")
            
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 出错了: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
