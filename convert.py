from pydub import AudioSegment
from mutagen.easymp4 import EasyMP4
from mutagen.mp3 import EasyMP3

def convert_m4a_to_mp3(input_file, output_file):
    # 加载M4A文件
    audio = AudioSegment.from_file(input_file, format="m4a")
    
    # 导出为MP3文件
    audio.export(output_file, format="mp3")
    
    # 复制标签信息
    m4a_tags = EasyMP4(input_file)
    mp3_tags = EasyMP3(output_file)
    
    for tag in m4a_tags:
        mp3_tags[tag] = m4a_tags[tag]
    
    mp3_tags.save()

if __name__ == "__main__":
    input_file = "input.m4a"
    output_file = "output.mp3"

    convert_m4a_to_mp3(input_file, output_file)

    print(f"转换完成：{input_file} -> {output_file}")
