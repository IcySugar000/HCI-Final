import json
import requests
import webbrowser


def open_website(url):
    webbrowser.open(url)
    return f"已为你打开：{url}"


def get_weather(location):
    with open("config.json", "r") as f:
        key = json.load(f)['weather']['key']

    geocode_url = f"https://restapi.amap.com/v3/geocode/geo?address={location}&output=json&key={key}"
    response = requests.get(geocode_url)
    geocode_data = response.json()
    geocode = geocode_data["geocodes"][0]["adcode"]

    weather_url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={geocode}&key={key}"
    response = requests.get(weather_url)
    weather_data = response.json()["lives"][0]

    msg = f"""以下是{weather_data["city"]}的天气信息：
    天气现象：{weather_data["weather"]}
    实时气温：{weather_data["temperature"]}（摄氏度)
    风向：{weather_data["winddirection"]}
    风力：{weather_data["windpower"]}（级）
    空气湿度：{weather_data["humidity"]}"""

    return msg


if __name__ == '__main__':
    open_website('1.tongji.edu.cn')
