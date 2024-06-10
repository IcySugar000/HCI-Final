import webbrowser


def open_website(url):
    webbrowser.open(url)
    return f"已为你打开：{url}"


if __name__ == '__main__':
    open_website('1.tongji.edu.cn')
