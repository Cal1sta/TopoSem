import os
from openai import OpenAI
import json
import threading
import re

'''d
model list：
o1-mini-2024-09-12
deepseek-v3-pro
deepseek-ai/DeepSeek-R1
gpt-4.1
gemini-2.5-pro
glm-4-long
grok-3
'''

model_name = "gemini-2.5-pro"
output_dir = f'./1-SemanticParser/output/{model_name}'

os.makedirs(output_dir, exist_ok=True)

client = OpenAI(
    api_key="",
    base_url = "https://api.openai.com/v1"
)


with open('./1-SemanticParser/prompt.txt', 'r', encoding='utf-8') as f1:
    prompt_text = f1.read()
with open('./1-SemanticParser/input/building_ontology/ontology_test.ttl', 'r', encoding='utf-8') as f2:
    building_data = f2.read()
with open('./1-SemanticParser/input/device_list/device_test.json', 'r', encoding='utf-8') as f3:
    device_data = f3.read()


rule_files = []
rule_path = './1-SemanticParser/input/rule_description/rule_test.txt'
with open(rule_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()


chunk_size = 30  

for i in range(0, len(lines), chunk_size):
    chunk = lines[i:i+chunk_size]
    split_path = os.path.join(output_dir, f'rule_split_{i//chunk_size+1}.txt')
    with open(split_path, 'w', encoding='utf-8') as f_split:
        f_split.writelines(chunk)
    rule_files.append(split_path)


output_jsons = []

def process_rule(idx, rule_file):
    print(f'------------------------{idx}th chunk------------------------')
    with open(rule_file, 'r', encoding='utf-8') as f:
        rule_text = f.read()

    full_prompt = f'''
{prompt_text}\n
-------------------------------
#input1-rule text:
{rule_text}\n
-------------------------------
#input2.device attributes list (JSON format):
{device_data}\n
#input3.building ontology information (e.g. excerpt based on Brick Schema):
{building_data}\n
'''

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": full_prompt,
            }
        ],
        model=model_name,
        stream=False,
        max_completion_tokens=65536
    )
    result = chat_completion.choices[0].message.content

    result = re.sub(r'^<think>.*?</think>\s*', '', result, flags=re.DOTALL)
    result = result.lstrip('\n')
    if result.startswith('```json'):
        result = result[len('```json'):].strip()
    if result.endswith('```'):
        result = result[:-len('```')].strip()


    output_path_split = os.path.join(output_dir, f'result-{idx}.json')
    with open(output_path_split, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f"{idx}th chunk saved to: {output_path_split}")


threads = []
for idx, rule_file in enumerate(rule_files, 1):
    t = threading.Thread(target=process_rule, args=(idx, rule_file))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
