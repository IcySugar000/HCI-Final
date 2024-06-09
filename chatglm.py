import httpx
import asyncio
from zhipuai import ZhipuAI


class LLM:
    def __init__(self):
        self.system_prompt = """你是一个语音助手，你需要根据用户的需求来进行回复，帮其完成相应任务"""
        self.tools = []
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
            tools=self.tools
        )

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
