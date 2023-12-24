import json
import re
import time
import json
import os
from openai import OpenAI
client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)
count = ['first', 'second', 'third', 'fourth', 'fifth',
         'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth', 'thirteenth', 'fourteenth', 'fifteenth', 'sixteenth', 'seventeenth', 'eighteenth', 'nineteenth', 'twentieth', 'twenty-first', 'twenty-second', 'twenty-third', 'twenty-fourth', 'twenty-fifth', 'twenty-sixth', 'twenty-seventh', 'twenty-eighth', 'twenty-ninth', 'thirtieth', 'thirty-first']


def translate(sentences, lang_target):
    my_properties = {}
    for i in range(len(sentences)):
        my_properties[count[i]] = {
            'type': 'string',
            'description': f'The {count[i]} translation part.'
        }
    tools = [
        {
            "type": "function",
            "function": {
                'name': 'translation',
                'description': f'Translate the {len(sentences)} parts of the user input into {lang_target}, each part of the user input corresponds to a part of the {lang_target}, the result must also be {len(sentences)} parts, and each part of the translated content can not be empty.',
                'parameters': {
                    'type': 'object',
                    'properties': my_properties
                }
            }
        }
    ]
    while True:
        try:
            sentences_description = ''
            for i in range(len(sentences)):
                sentences_description += sentences[i] + \
                    '\n----------------------------------\n'
            # print(sentences_description)
            messages = [{"role": "user", "content": sentences_description}]
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                tools=tools,
                tool_choice={"type": "function",
                             "function": {"name": "translation"}},
                temperature=0.0
            )
            break
        except Exception as e:
            print(e)
            time.sleep(5)  # 等待 5 秒后重试

    json_arguments = completion.choices[0].message.tool_calls[0].function.arguments
    arguments_dict = json.loads(json_arguments)
    values = arguments_dict.values()
    values_list = list(values)
    print('进入翻译器')
    print('长度为：'+str(len(values_list)))
    print(values_list)

    if len(values_list) != len(sentences) or values_list[-1] == '':
        values_list = remove_empty_strings(values_list)
        result_arr = split_arr(values_list, len(sentences))
        print('更改成功，长度为：'+str(len(result_arr)))
        print(result_arr)
        return result_arr
    else:
        return values_list


def remove_empty_strings(arr):
    return list(filter(None, arr))


def find_top_three_indices(nums, count):
    indices = sorted(range(len(nums)), key=lambda x: nums[x], reverse=True)
    return indices[:count]


def find_longest_string_index(array):
    longest_index = 0
    longest_length = len(array[0])

    for i in range(1, len(array)):
        if len(array[i]) > longest_length:
            longest_length = len(array[i])
            longest_index = i

    return longest_index


def split_arr(translation_arr, sentences_length):
    longest_index = find_longest_string_index(translation_arr)
    text = translation_arr[longest_index]
    punctuation_mark = ['。', '，', '.', ',']
    for mark in punctuation_mark:
        if mark in text:
            sentences = text.split(mark)
            sentences = [sentence for sentence in sentences if sentence]
            if len(sentences) > 1:
                translation_arr[longest_index] = mark.join(sentences[:-1])
                translation_arr.insert(longest_index+1, sentences[-1])
                if len(translation_arr) == sentences_length:
                    return translation_arr
                else:
                    return split_arr(translation_arr, sentences_length)
