import json
import httpx
import asyncio
from zhipuai import ZhipuAI
from utils import *

base_prompt = """你是一个语音助手，你的用户群体是同济大学的大学生，你需要根据用户的需求来进行回复，帮其完成相应任务

这里是一些必要的信息，在用户需要时你可以提供：
1系统网址：1.tongji.edu.cn
canvas系统网址：canvas.tongji.edu.cn
同济邮箱网址：mail.tongji.edu.cn
以上网址均不需要连接校园网即可访问
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "根据用户提供的信息，打开指定的网页",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要打开的网站的网址",
                    },
                },
                "required": ["url"],
            },
        }
    }
]


class LLM:
    def __init__(self):
        self.system_prompt = base_prompt
        self.tools = tools
        self.messages = [{"role": "system", "content": self.system_prompt}]

        proxy_url = "http://127.0.0.1:7890"
        httpx_client = httpx.Client(proxies={"http://": proxy_url, "https://": proxy_url}, verify=False)
        self.client = ZhipuAI(api_key="4dbf2bd2a03cfc99887c4933d97d05eb.wZf6smU1wB8F19sW", http_client=httpx_client)

    async def get_reply_async(self, messages: str):
        self.messages.append({"role": "user", "content": messages})
        print(self.messages)

        response = self.client.chat.completions.create(
            model="glm-4",  # 填写需要调用的模型名称
            messages=self.messages,
            tools=tools,
            tool_choice="auto"
        )

        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            args = tool_call.function.arguments
            if tool_call.function.name == "open_website":
                return_msg = open_website(**json.loads(args))
                return return_msg
        else:
            content = response.choices[0].message.content
            return content

    def get_reply(self, messages: str):
        loop = asyncio.get_event_loop()
        task = loop.create_task(self.get_reply_async(messages))
        loop.run_until_complete(task)
        return task.result()


if __name__ == "__main__":
    llm = LLM()
    response = llm.get_reply("这是一条测试信息")
    print(response)
