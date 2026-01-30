import os
import re
import json
import threading
from openai import OpenAI

model_name = "gemini-2.5-pro"
output_dir = './2-ChannelInference_TopoFilter/output'
input_rule = 'virtualBuilding'
os.makedirs(output_dir, exist_ok=True)

client = OpenAI(
    api_key="",
    base_url="https://api.openai.com/v1"
)


with open('./2-ChannelInference_TopoFilter/prompt.txt', 'r', encoding='utf-8') as f1:
    prompt_text = f1.read()


with open(f'./2-ChannelInference_TopoFilter/input/{input_rule}.json', 'r', encoding='utf-8') as f2:
    rule_data = json.load(f2)

# slice size
slice_size = 20  

# slice data
if isinstance(rule_data, list):
    slices = [rule_data[i:i+slice_size] for i in range(0, len(rule_data), slice_size)]
elif isinstance(rule_data, dict):
    # if dict, group by top level key
    keys = list(rule_data.keys())
    slices = [{k: rule_data[k] for k in keys[i:i+slice_size]} for i in range(0, len(keys), slice_size)]
else:
    slices = [rule_data]

# save result to independent folder
slice_output_dir = os.path.join(output_dir, f'{input_rule}_{model_name}_slices')
os.makedirs(slice_output_dir, exist_ok=True)

output_json_paths = []

def call_llm(slice_data, idx):
    full_prompt = f'''
{prompt_text}\n
-------------------------------
Input:
Structured Rules Data - JSON format:
{json.dumps(slice_data, ensure_ascii=False, indent=2)}\n
'''
    print(f'Processing slice {idx+1}/{len(slices)}...')
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": full_prompt}],
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
    output_path = os.path.join(slice_output_dir, f'slice_{idx+1}.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)
        print(f'Slice {idx+1} processed and saved to {output_path}')
    output_json_paths.append(output_path)

threads = []
for idx, slice_data in enumerate(slices):
    t = threading.Thread(target=call_llm, args=(slice_data, idx))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

# merge all outputs to one file (put in slice folder, sorted by slice order)
merged_results = []
# sorted by slice_0.json, slice_1.json, ...
sorted_paths = sorted(output_json_paths, key=lambda x: int(re.search(r'slice_(\d+)\.json', x).group(1)))
for path in sorted_paths:
    with open(path, 'r', encoding='utf-8') as f:
        try:
            data = json.loads(f.read())
            if isinstance(data, list):
                merged_results.extend(data)
            else:
                merged_results.append(data)
        except Exception:
            merged_results.append(f.read())

output_path = os.path.join(slice_output_dir, f'{input_rule}_{model_name}_merged_output.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(merged_results, f, ensure_ascii=False, indent=2)
print(f"All results merged to: {output_path}")
