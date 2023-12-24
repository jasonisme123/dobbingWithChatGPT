import Bilingual
import json
from moviepy.editor import *
import handle_audio
import os
import glob
from pydub import AudioSegment
import cv2
import subprocess


def delete_fileDir(folder_path, suffix):
    # 获取文件夹下所有的MP4和WAV文件路径
    media_files = glob.glob(os.path.join(folder_path, "*."+suffix))

    for media_file in media_files:
        os.remove(media_file)


def delete_file(file_path):
    try:
        os.remove(file_path)
    except OSError as e:
        print(f"删除文件 {file_path} 时发生错误: {e}")


def video2audio(video_name):
    audio = AudioSegment.from_file(video_name, format="mp4")
    audio.export("overview.wav", format="wav")


def delete_all_files():
    delete_fileDir('./audios/', 'wav')
    delete_fileDir('./new_audios/', 'wav')
    delete_fileDir('./testaudio/', 'wav')
    delete_fileDir('./videos/', 'mp4')
    delete_file('overview.wav')
    delete_file('overview.mp4')
    delete_file('hiahia.wav')
    delete_file('hiahia.mp4')
    delete_file('subtitle.srt')


def audio2srt(target, test_length, isSpeechVerification):
    handle_audio.main(target, test_length, isSpeechVerification)


def change_video_name(video_name):
    # 获取当前目录
    current_dir = os.getcwd()
    # 遍历当前目录下的文件
    for file_name in os.listdir(current_dir):
        # 检查文件是否是MP4格式
        if file_name.endswith(".mp4"):
            # 构造新的文件名
            new_file_name = video_name
            # 检查新的文件名是否已存在
            if os.path.exists(new_file_name):
                break
            # 执行重命名操作
            os.rename(file_name, new_file_name)
            break

# 将一个mp4与一个wav文件合并起来


def merge_mp4_and_wav(mp4_file, wav_file):
    video = VideoFileClip(mp4_file)
    audio = AudioFileClip(wav_file)
    video.set_audio(audio).write_videofile("output.mp4")
    audio.close()
    video.close()


def video_merge_srt(input_mp4="output.mp4"):
    output_mp4 = "your_video.mp4"
    subtitles_srt = 'subtitle.srt'
    command = [
        "ffmpeg",
        "-i",
        input_mp4,
        "-vf",
        f"subtitles={subtitles_srt}",
        output_mp4,
    ]

    subprocess.run(command, check=True)


def main():
    video_name = 'overview.mp4'
    target = 'Chinese'  # 目标language
    test_length = 0
    isSpeechVerification = False
    change_video_name(video_name)
    video2audio(video_name)
    audio2srt(target, test_length, isSpeechVerification)
    merge_mp4_and_wav('hiahia.mp4', 'hiahia.wav')
    video_merge_srt()
    delete_all_files()  # 用于删除程序运行过程中产成的音视频文件


if __name__ == '__main__':
    main()
