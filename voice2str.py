import asyncio

import websocket
import datetime
import hashlib
import base64
import hmac
import json
import time
from urllib.parse import urlencode
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread

import numpy as np

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, AudioFile):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.AudioFile = AudioFile

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo":1,"vad_eos":10000, "dwa":"wpgs"}

    # 生成url
    def create_url(self):
        url = 'wss://ws-api.xfyun.cn/v2/iat'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        # print("date: ",date)
        # print("v: ",v)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        # print('websocket url :', url)
        return url


class Resolver:
    """
    用于解析/整合WebSocket信息
    """
    def __init__(self, file_name):
        self.data = []
        self.done = False

        self.wsParam = Ws_Param(APPID='492e3872',
                                APISecret='YTcyNTRhMWQwZTM4NDI1OTg4MGRlMzZl',
                                APIKey='afbba808b46481e054f3e2cc695068bf',
                                AudioFile=file_name)
        websocket.enableTrace(False)
        wsUrl = self.wsParam.create_url()
        self.ws = websocket.WebSocketApp(wsUrl, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        self.ws.on_open = self.on_open
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def transfer_msg_to_list(self, msg):
        new_data = []
        for i in msg["ws"]:
            new_data.append(i["cw"][0]["w"])
        return new_data

    def add_msg(self, msg: dict):
        if "rg" not in msg.keys():
            self.data.append(self.transfer_msg_to_list(msg))
        else:
            self.data.append([])
            index_from, index_to = msg['rg'][0]-1, msg['rg'][1]-1
            for i in range(index_from, index_to+1):
                self.data[i] = []
            self.data[index_from] = self.transfer_msg_to_list(msg)

        if msg['ls']:
            self.ws.close()
            self.done = True

    def get_str(self):
        result = ""
        for l in self.data:
            result += ''.join(l)
        return result

    def get_complete_result(self):
        async def async_wait_for_done():
            while not self.done:
                await asyncio.sleep(0.04)
            return self.get_str()

        loop = asyncio.get_event_loop()
        task = asyncio.ensure_future(async_wait_for_done())
        loop.run_until_complete(task)
        return task.result()

    # 收到websocket消息的处理
    def on_message(self, message):
        try:
            code = json.loads(message)["code"]
            sid = json.loads(message)["sid"]
            if code != 0:
                errMsg = json.loads(message)["message"]
                print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))
    
            else:
                self.add_msg(json.loads(message)["data"]["result"])
        except Exception as e:
            print("receive msg,but parse exception:", e)

    # 收到websocket错误的处理
    def on_error(self, error):
        print("### error:", error)

    # 收到websocket关闭的处理
    def on_close(self, a, b):
        pass
        # print("### closed ###")

    # 收到websocket连接建立的处理
    def on_open(self):
        # print("### opening ###")

        def run(*args):
            frameSize = 1280  # 每一帧的音频大小
            interval = 0.04  # 发送音频间隔(单位:s)
            status = STATUS_FIRST_FRAME  # 音频的状态信息，标识音频是第一帧，还是中间帧、最后一帧

            with open(self.wsParam.AudioFile, "rb") as fp:
                while True:
                    buf = fp.read(frameSize)
                    # 文件结束
                    if not buf:
                        status = STATUS_LAST_FRAME
                    # 第一帧处理
                    # 发送第一帧音频，带business 参数
                    # appid 必须带上，只需第一帧发送
                    if status == STATUS_FIRST_FRAME:

                        d = {"common": self.wsParam.CommonArgs,
                             "business": self.wsParam.BusinessArgs,
                             "data": {"status": 0, "format": "audio/L16;rate=16000",
                                      "audio": str(base64.b64encode(buf), 'utf-8'),
                                      "encoding": "lame"}}
                        d = json.dumps(d)
                        self.ws.send(d)
                        status = STATUS_CONTINUE_FRAME
                    # 中间帧处理
                    elif status == STATUS_CONTINUE_FRAME:
                        d = {"data": {"status": 1, "format": "audio/L16;rate=16000",
                                      "audio": str(base64.b64encode(buf), 'utf-8'),
                                      "encoding": "lame"}}
                        self.ws.send(json.dumps(d))
                    # 最后一帧处理
                    elif status == STATUS_LAST_FRAME:
                        d = {"data": {"status": 2, "format": "audio/L16;rate=16000",
                                      "audio": str(base64.b64encode(buf), 'utf-8'),
                                      "encoding": "lame"}}
                        self.ws.send(json.dumps(d))
                        # time.sleep(1)
                        break
                    # 模拟音频采样间隔
                    time.sleep(interval)

        thread.start_new_thread(run, ())


def wav2pcm(wavfile, pcmfile, data_type=np.int16):
    f = open(wavfile, "rb")
    f.seek(0)
    f.read(44)
    data = np.fromfile(f, dtype= data_type)
    data.tofile(pcmfile)


def save_wav2pcm(wav_name):
    pcm_name = wav_name.replace(".wav", ".pcm")
    with open(pcm_name, "wb") as f_pcm:
        wav2pcm(wav_name, f_pcm)


if __name__ == "__main__":
    # 测试时候在此处正确填写相关信息即可运行
    time1 = datetime.now()
    # save_wav2pcm("Cappuccino.wav")

    resolver = Resolver("Cappuccino_16k.mp3")
    print(resolver.get_str())

    time2 = datetime.now()
    print(time2-time1)
