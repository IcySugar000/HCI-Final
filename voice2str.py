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
import threading

import pyaudio
from pydub import AudioSegment
from io import BytesIO

import numpy as np

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo": 1,"vad_eos":10000, "dwa":"wpgs"}

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
        # print('websocket url :', url)
        return url


class Resolver:
    """
    用于解析/整合WebSocket信息
    """
    def __init__(self):
        self.data = []
        self.done = False

        with open("config.json", "r") as f:
            self.config = json.load(f)['voice2str']

        self.wsParam = Ws_Param(APPID=self.config['APPID'],
                                APISecret=self.config['APISecret'],
                                APIKey=self.config['APIKey'])
        websocket.enableTrace(False)
        wsUrl = self.wsParam.create_url()
        self.ws = websocket.WebSocketApp(wsUrl, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        self.ws.on_open = self.on_open

    def start(self):
        ws_thread = threading.Thread(target=self.ws.run_forever, kwargs={"sslopt": {"cert_reqs": ssl.CERT_NONE}})
        ws_thread.daemon = True
        ws_thread.start()
        
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
    def on_message(self, ws, message):
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
    def on_error(self, ws, error):
        print("### error:", error)

    # 收到websocket关闭的处理
    def on_close(self, ws, a, b):
        pass
        print(self.get_str())
        # print("### closed ###")

    # 收到websocket连接建立的处理
    def on_open(self, ws):
        # print("### opening ###")

        def run(*args):
            frameSize = 1280  # 每一帧的音频大小
            interval = 0.04  # 发送音频间隔(单位:s)
            status = STATUS_FIRST_FRAME  # 音频的状态信息，标识音频是第一帧，还是中间帧、最后一帧

            p=pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=frameSize)

            while True:
                buf = stream.read(frameSize)

                # 文件结束
                if not buf or self.done:
                    if status == STATUS_FIRST_FRAME:
                        break
                    status = STATUS_LAST_FRAME
                # 第一帧处理
                # 发送第一帧音频，带business 参数
                # appid 必须带上，只需第一帧发送
                if status == STATUS_FIRST_FRAME:
                    d = {
                            "common": self.wsParam.CommonArgs,
                            "business": self.wsParam.BusinessArgs,
                            "data": {
                                "status": 0,
                                "format": "audio/L16;rate=16000",
                                "audio": str(base64.b64encode(buf), 'utf-8'),
                                "encoding": "raw"
                            }
                        }
                    status = STATUS_CONTINUE_FRAME
                # 中间帧处理
                elif status == STATUS_CONTINUE_FRAME:
                    d = {
                            "data": {
                                "status": 1, 
                                "format": "audio/L16;rate=16000",
                                "audio": str(base64.b64encode(buf), 'utf-8'),
                                "encoding": "raw"
                            }
                        }
                # 最后一帧处理
                elif status == STATUS_LAST_FRAME:
                    d = {
                            "data": {
                                "status": 2, 
                                "format": "audio/L16;rate=16000",
                                "audio": str(base64.b64encode(buf), 'utf-8'),
                                "encoding": "raw"
                            }
                        }
                # 发送数据包
                try:
                    ws.send(json.dumps(d))
                    if status == STATUS_LAST_FRAME:
                        break
                except websocket.WebSocketConnectionClosedException as e:
                    print("Connection closed: ", e)
                    break
                # 模拟音频采样间隔
                time.sleep(interval)

            stream.stop_stream()
            stream.close()
            p.terminate()

        threading.Thread(target=run, args=(ws,)).start()

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
    resolver = Resolver("test.mp3")
    print(resolver.get_str())
