import paddle
from paddlespeech.cli.vector import VectorExecutor
from pydub import AudioSegment
import soundfile as sf
from scipy import signal
import wave
import asyncio
import edge_tts
from moviepy.editor import *
from transformers import pipeline

pipe = pipeline("audio-classification",
                model="alefiury/wav2vec2-large-xlsr-53-gender-recognition-librispeech")


voice_speaker = []
speaker_gender = []  # 1 男 0 女
embedding_speaker = []
embedding_speaker_voice = []


def get_audio_embedding(audio_file):
    vector_executor = VectorExecutor()
    audio_emb = vector_executor(
        model='ecapatdnn_voxceleb12',
        sample_rate=16000,
        # Set `config` and `ckpt_path` to None to use pretrained model.
        config=None,
        ckpt_path=None,
        audio_file=audio_file,
        device=paddle.get_device())
    return audio_emb


def get_score(audio1_emb, audio2_emb):
    vector_executor = VectorExecutor()
    score = vector_executor.get_embeddings_score(audio1_emb, audio2_emb)
    return float(score)


def mp4_to_wav(mp4file, wavfile):
    audio = AudioSegment.from_file(mp4file, format="mp4")
    audio.export(wavfile, format="wav")


def get_sample_rate(input_file):
    # 打开WAV音频文件
    with wave.open(input_file, 'r') as wav_file:
        sample_rate = wav_file.getframerate()

    return sample_rate


def change_sample_rate(input_file, output_file):
    audio, sample_rate = sf.read(input_file)
    target_sample_rate = 16000
    resample_ratio = target_sample_rate / sample_rate
    resample_audio = signal.resample(audio, int(len(audio) * resample_ratio))
    sf.write(output_file, resample_audio, target_sample_rate)


def get_speaker(audio_name, index, start_time, end_time):
    global voice_speaker
    global speaker_gender
    global embedding_speaker
    global embedding_speaker_voice

    duration = float(end_time)-float(start_time)
    audio_file = './testaudio/'+str(index)+'.wav'
    audio_clip = AudioFileClip(audio_name)
    audio_subclip = audio_clip.subclip(start_time, end_time)
    audio_subclip.write_audiofile(audio_file)
    # 释放资源
    audio_subclip.close()
    audio_clip.close()

    audio_sample_rate = get_sample_rate(audio_file)
    if int(audio_sample_rate) != 16000:
        change_sample_rate(audio_file, audio_file)

    max_score = 0
    max_index = 0
    cur_emb = get_audio_embedding(audio_file)
    for i, emb in enumerate(embedding_speaker):
        score = get_score(cur_emb, emb)
        if score > max_score:
            max_score = score
            max_index = i

    if max_score > 0.3:
        return embedding_speaker_voice[max_index]
    else:
        try:
            if float(duration) < 1.5:
                return embedding_speaker_voice[max_index]
            else:
                embedding_speaker.append(cur_emb)
                results = pipe(audio_file)
                gender = 1 if results[0]["label"] == "male" else 0
                pre_speaker_gender_len = len(voice_speaker)
                for i in range(len(speaker_gender)):
                    if speaker_gender[i] == gender:
                        embedding_speaker_voice.append(voice_speaker[i])
                        voice_speaker.pop(i)
                        break
                cur_speaker_gender_len = len(voice_speaker)
                if cur_speaker_gender_len == pre_speaker_gender_len:
                    raise Exception('角色不足')
                return embedding_speaker_voice[-1]
        except Exception as e:
            raise e


def init_speaker(lang_target):
    global voice_speaker
    global speaker_gender
    match lang_target:
        case 'Chinese':
            voice_name = "zh-CN"
        case 'English':
            voice_name = "en-US"
        case 'Japanese':
            voice_name = "ja-JP"
        case 'Korean':
            voice_name = "ko-KR"
        case 'Russian':
            voice_name = "ru-RU"
        case _:
            raise Exception('语言不支持')

    while True:
        try:
            voices = asyncio.run(edge_tts.list_voices())
            break
        except Exception as e:
            print(e)
            time.sleep(5)  # 等待 5 秒后重试

    for voice in voices:
        if voice['ShortName'].startswith(voice_name):
            voice_speaker.append(voice['ShortName'])
            speaker_gender.append(int(voice['Gender'] == 'Male'))
