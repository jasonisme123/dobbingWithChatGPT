名称:ChatGPT视频配音


功能:

1、实现音频转录,使用的模型是 Systran/faster-whisper-small

2、文本翻译,使用ChatGPT-3.5-turbo,不建议使用GPT-4,因为翻译是一个简单的任务,不建议浪费金钱

3、配音,使用的是edge-tts

4、添加字幕

参数:

1、在app.py中,test_length用于设置配音的速度,如果为0则默认速度为"+15%"

2、isSpeechVerification用于是否识别不同说话者的声音,实现不同角色配音,使用的模型是PaddlePaddle/PaddleSpeech/ecapatdnn_voxceleb12,以及alefiury/wav2vec2-large-xlsr-53-gender-recognition-librispeech

3、target则是目标翻译语言

4、在handle_audio.py中,TRAN_COUNT用于每次翻译的句子数

5、MERGE_SIZE用于当视频剪切的数量达到指定数值时,则进行合并.因为如果剪切的视频过多最后进行合并时会出现内存空间不足的问题


