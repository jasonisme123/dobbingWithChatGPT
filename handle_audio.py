import json
from pydub import AudioSegment
from moviepy.editor import *
from datetime import timedelta
from faster_whisper import WhisperModel
import re
import os
import Bilingual
import edge_tts
import asyncio
from functools import reduce
import whoSpeak
speed_arr = []
last_end_time = 0
video_last_end_time = 0
target = ''
current_time = 0
TRAN_COUNT = 10  # 每次翻译的数量
MERGE_SIZE = 50  # 当视频数量超过50时，进行拼接


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]


def get_audios_files(dirs):
    folder_path = dirs
    """递归获取指定文件夹下的所有文件"""
    files = []
    # 遍历文件夹下的所有文件和文件夹
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        # 判断是否是文件，如果是文件则添加到列表中
        if os.path.isfile(item_path):
            files.append(item_path)
        # 如果是文件夹，则递归获取该文件夹下的所有文件
        elif os.path.isdir(item_path):
            files.extend(list_all_files(item_path))

    sorted_files = sorted(
        files, key=lambda x: natural_sort_key(os.path.basename(x)))
    return sorted_files


def get_translate_text(texts):
    global target
    translate_text = Bilingual.translate(texts, target)
    return translate_text


def delete_files_except(folder_path, preserved_file):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename != preserved_file:
            os.remove(file_path)


def rename_file(folder_path, old_file_name, new_file_name):
    old_file_path = os.path.join(folder_path, old_file_name)
    new_file_path = os.path.join(folder_path, new_file_name)

    if os.path.exists(old_file_path):
        os.rename(old_file_path, new_file_path)


def merge_mp4_files(folder_path, output_file):
    video_clips = []
    tfiles = get_audios_files(folder_path)
    # 遍历文件夹中的每个文件
    for i, file_name in enumerate(tfiles):
        if file_name.endswith(".mp4"):
            clip = VideoFileClip(file_name).without_audio()
            video_clips.append(clip)

     # 合并视频片段
    final_clip = concatenate_videoclips(video_clips)
    # 保存合并后的视频
    final_clip.write_videofile(output_file)
    for clip in video_clips:
        clip.close()
    final_clip.close()


def transcribe(audio_name, voice_spped, isSpeechVerification, cur_voice):
    global TRAN_COUNT
    global MERGE_SIZE
    model_size = "small"
    model = WhisperModel(model_size, compute_type="float32")
    segments, _ = model.transcribe(audio_name, word_timestamps=True)
    sentences_arr = []
    segment_start_arr = []
    segment_end_arr = []
    for i, segment in enumerate(segments):
        print('current_time'+str(segment.end))
        if i > 0 and i % MERGE_SIZE == 0:
            merge_mp4_files('./videos', './videos/temp.mp4')
            delete_files_except('./videos', 'temp.mp4')
            rename_file('./videos', 'temp.mp4', str(i//MERGE_SIZE) + '.mp4')

        segment_text = segment.text.strip()
        sentences_arr.append(segment_text)
        segment_start_arr.append("{:.3f}".format(segment.start))
        segment_end_arr.append("{:.3f}".format(segment.end))

        if len(sentences_arr) % TRAN_COUNT == 0:
            translate_text_arr = get_translate_text(sentences_arr)
            for j, translate_text in enumerate(translate_text_arr):
                if isSpeechVerification:
                    voice = whoSpeak.get_speaker(
                        'overview.wav', i-TRAN_COUNT+j+1, float(segment_start_arr[j]), float(segment_end_arr[j]))
                else:
                    voice = cur_voice
                text_2_audio(translate_text, segment_start_arr[j],
                             segment_end_arr[j], i-TRAN_COUNT+j+1, voice_spped, voice)
            sentences_arr = []
            segment_start_arr = []
            segment_end_arr = []

    if len(sentences_arr) > 0:
        translate_text_arr = get_translate_text(sentences_arr)
        pre_index = i-len(sentences_arr)+1

        for j, translate_text in enumerate(translate_text_arr):
            if isSpeechVerification:
                voice = whoSpeak.get_speaker(
                    'overview.wav', pre_index+j, float(segment_start_arr[j]), float(segment_end_arr[j]))
            else:
                voice = cur_voice
            text_2_audio(translate_text, segment_start_arr[j], segment_end_arr[j],
                         pre_index+j, voice_spped, voice)

    merge_all_wav('./new_audios', 'hiahia.wav')
    merge_mp4_files('./videos', 'hiahia.mp4')


def get_overflow_video(video_name, overflow_second, start_time, end_time, index):
    # print('hey, overflow')
    clip = VideoFileClip(video_name)
    trimmed_clip = clip.subclip(start_time, end_time).without_audio()
    slow_speed = round(trimmed_clip.duration /
                       (overflow_second+trimmed_clip.duration), 5)
    trimmed_clip.fx(vfx.speedx, slow_speed).write_videofile(
        './videos/'+str(index)+'.mp4')

    trimmed_clip.close()
    clip.close()


def cut_video(video_name, start_time, end_time, index):
    clip = VideoFileClip(video_name)
    trimmed_clip = clip.subclip(start_time, end_time).without_audio()
    trimmed_clip.write_videofile('./videos/'+str(index)+'.mp4')
    trimmed_clip.close()
    clip.close()


def cut_audio(silence_duration, index):
    silence_segment = AudioSegment.silent(duration=int(silence_duration*1000))
    silence_segment.export('./new_audios/'+str(index)+'.wav', format="wav")


def text_insert_srt(text, start_time, end_time, index):
    output_file = 'subtitle.srt'
    with open(output_file, 'a', encoding='utf-8') as output:
        output.write(str(index) + '\n')
        start = adjust_time(start_time)
        end = adjust_time(end_time)
        output.write(f"{start} --> {end}\n")
        output.write(text)
        output.write('\n\n')


def adjust_time(time_str):
    # 将字符串转换为浮点数
    time_in_seconds = float(time_str)

    # 将浮点数转换为时间差对象
    delta = timedelta(seconds=time_in_seconds)

    # 计算出小时、分钟、秒和毫秒
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = delta.microseconds // 1000

    # 将时间格式化为"00:02:12,560"的格式
    result = f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    return result


def text_2_audio(text, start_time, end_time, index, voice_spped, voice):
    global video_last_end_time
    global last_end_time
    global target
    global tts
    global current_time
    audio_filePath = './audios/'+str(index)+'.wav'

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            tts = edge_tts.Communicate(
                text=text, voice=voice, rate=voice_spped, volume='+80%')
            break
        except Exception as e:
            time.sleep(5)  # 等待 5 秒后重试
    temp_audio_filePath = './audios/'+str(index)+'.mp3'
    loop.run_until_complete(tts.save(temp_audio_filePath))
    loop.close()
    convert_mp3_to_wav(temp_audio_filePath, audio_filePath)
    delete_audio_file(temp_audio_filePath)

    audio_duration = get_mp3_duration(audio_filePath)

    if (audio_duration > (float(end_time)-float(start_time))):
        get_overflow_video('overview.mp4', audio_duration - (float(end_time) -
                           float(start_time)), float(video_last_end_time), float(end_time), index)
    else:
        cut_video('overview.mp4', float(
            video_last_end_time), float(end_time), index)

    silence_gap = (float(start_time) - float(last_end_time))*1000
    audio_gap = ((float(end_time)-float(start_time)) - audio_duration)*1000

    if audio_gap < 0:
        merge_mp3_with_silence(audio_filePath, silence_gap, 0, index)
    else:
        merge_mp3_with_silence(audio_filePath, silence_gap, audio_gap, index)

    if index == 0:
        if audio_gap >= 0:
            text_insert_srt(text, start_time, end_time, index+1)
            current_time = float(end_time)
        else:
            current_time = float(end_time)-audio_gap/1000
            text_insert_srt(text, start_time, current_time, index+1)
    else:
        pre_current_time = current_time+silence_gap/1000
        if audio_gap >= 0:
            current_time = current_time+silence_gap / \
                1000+(float(end_time)-float(start_time))
        else:
            current_time = current_time+silence_gap/1000+audio_duration
        text_insert_srt(text, pre_current_time, current_time, index+1)

    last_end_time = end_time
    video_last_end_time = end_time


def merge_all_wav(folder_path, output_file):
    audio_clips = []
    tfiles = get_audios_files(folder_path)
    for file_name in tfiles:
        if file_name.endswith(".wav"):
            audio_clips.append(AudioSegment.from_wav(file_name))
    combined = reduce(lambda a, b: a + b, audio_clips)
    # 导出到新的音频文件
    combined.export(output_file, format='wav')


def merge_mp3_with_silence(mp3_file, gap_silence_duration, remain_silence_duration, index):
    audio2 = AudioSegment.from_wav(mp3_file)
    # 创建静音段
    gap_silence_segment = AudioSegment.silent(
        duration=int(gap_silence_duration))
    remain_silence_segment = AudioSegment.silent(
        duration=int(remain_silence_duration))
    # 合并音频文件
    merged_audio = gap_silence_segment + audio2 + remain_silence_segment
    # 导出合并后的音频文件
    merged_audio.export('./new_audios/'+str(index)+'.wav', format="wav")


def get_mp3_duration(file_path):
    sound = AudioSegment.from_wav(file_path)
    duration_in_seconds = len(sound) / 1000
    return duration_in_seconds


def convert_mp3_to_wav(mp3_file, wav_file):
    audio = AudioSegment.from_mp3(mp3_file)
    audio.export(wav_file, format='wav')


def delete_audio_file(file_path):
    try:
        os.remove(file_path)
        # print(f"音频文件 {file_path} 已成功删除")
    except OSError as e:
        print(f"删除音频文件 {file_path} 时发生错误: {e}")


def mywhisper(audio_name, length, lang_target):
    voice_name = ''
    match lang_target:
        case 'Chinese':
            voice_name = "zh-CN-YunxiNeural"
        case 'English':
            voice_name = "en-US-EricNeural"
        case 'Japanese':
            voice_name = "ja-JP-NanamiNeural"
        case 'Korean':
            voice_name = "ko-KR-SunHiNeural"
        case 'Russian':
            voice_name = "ru-RU-SvetlanaNeural"
        case _:
            raise Exception('语言不支持')

    if length <= 0:
        return 15, voice_name

    model_size = "small"
    model = WhisperModel(model_size, compute_type="float32")
    segments, _ = model.transcribe(audio_name, word_timestamps=True)
    sentences_arr = []
    segment_start_arr = []
    segment_end_arr = []
    for i, segment in enumerate(segments):
        segment_text = segment.text.strip()
        sentences_arr.append(segment_text)
        segment_start_arr.append("{:.3f}".format(segment.start))
        segment_end_arr.append("{:.3f}".format(segment.end))

        length -= 1
        if length <= 0:
            break

    translate_text_arr = Bilingual.translate(sentences_arr, lang_target)
    for j, translate_text in enumerate(translate_text_arr):
        mytts(translate_text, 0, float(segment_end_arr[j]) -
              float(segment_start_arr[j]), j, voice_name, 0)

    return get_average(), voice_name


def mytts(text, vioce_speed, time_distance, index, voice_name, oscillate):
    global speed_arr
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            if vioce_speed >= 0:
                tts = edge_tts.Communicate(
                    text=text, voice=voice_name, rate='+'+str(vioce_speed)+'%', volume='+80%')
            else:
                tts = edge_tts.Communicate(
                    text=text, voice=voice_name, rate=str(vioce_speed)+'%', volume='+80%')

            break
        except Exception as e:
            print(e)
            time.sleep(5)  # 等待 5 秒后重试
    temp_audio_filePath = str(index)+'.mp3'
    loop.run_until_complete(tts.save(temp_audio_filePath))
    loop.close()
    sound = AudioSegment.from_mp3(temp_audio_filePath)
    duration_in_seconds = len(sound) / 1000

    # 允许误差在0.3秒以内,加速减速范围在(-50,50)
    if duration_in_seconds < time_distance and abs(duration_in_seconds - time_distance) > 0.3 and vioce_speed > -50 and oscillate-5 != 0:
        # 说明要减速
        mytts(text, vioce_speed-5, time_distance, index, voice_name, -5)
    elif duration_in_seconds > time_distance and abs(duration_in_seconds - time_distance) > 0.3 and vioce_speed < 50 and oscillate+5 != 0:
        # 说明要加速
        mytts(text, vioce_speed+5, time_distance, index, voice_name, 5)
    else:
        speed_arr.append(vioce_speed)
        os.remove(temp_audio_filePath)


def get_average():
    global speed_arr
    return round(sum(speed_arr) / len(speed_arr))


def main(lang_target, test_length, isSpeechVerification):
    global target
    target = lang_target
    if isSpeechVerification:
        whoSpeak.init_speaker(lang_target)
    pre_voice_spped, voice_name = mywhisper(
        'overview.wav', test_length, lang_target)
    if pre_voice_spped >= 0:
        voice_spped = '+'+str(pre_voice_spped)+'%'
    else:
        voice_spped = str(pre_voice_spped)+'%'

    transcribe('overview.wav', voice_spped, isSpeechVerification, voice_name)
