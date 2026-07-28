import json
import subprocess
import time
import sys

def generate_fallback(t):
    """Generate fallback description if Claude API fails"""
    section = t["section"]
    desc = t["desc"]
    header = t["header"]
    header_str = "、".join(h for h in header if h and not h.startswith("("))
    if header_str:
        return f"统计期内{section}相关数据如下表所示，涵盖{desc}，主要维度包括{header_str}，具体数值详见下表。"
    return f"统计期内{section}相关数据如下表所示，涵盖{desc}，具体数值详见下表。"

# Read tables info
with open("tables_info.json") as f:
    tables = json.load(f)

# Tables to skip
skip_tables = {58}
tables_to_process = [t for t in tables if t["idx"] not in skip_tables]

# Split into batches of 8
batches = [tables_to_process[i:i+8] for i in range(0, len(tables_to_process), 8)]

API_KEY = "sk-w4ENEt8TfHvdBcYpD5411c8a173a41CfAb9404AbB5DeAdA6"
URL = "https://oneapi-comate.baidu-int.com/v1/messages"

all_descriptions = {}

for batch_idx, batch in enumerate(batches):
    print(f"\n--- Batch {batch_idx+1}/{len(batches)} (tables {[t['idx'] for t in batch]}) ---", flush=True)
    
    tables_str = ""
    for t in batch:
        tables_str += f"\n表格{t['idx']}:\n  章节: {t['section']}\n  表头: {t['header']}\n  规模: {t['rows']}\n  内容概述: {t['desc']}\n"
    
    prompt = f'''你是公交车辆故障分析报告的数据分析师。请为以下每个表格生成一段白描式描述文字，用于补充在表格前。

要求：
1. 采用"具体数值+变化趋势+部件+区域地点+车号/分公司/线路等运营单位清单"的白描式结构
2. 所有具体数值用占位符表示（如 [次数]、[XX%]、[车辆数]、[次/万km]、[时长]）
3. 不要编造表格里没有的趋势或运营单位信息
4. 描述应自然流畅，像分析报告中的段落，不要分点列举
5. 每个表格一段描述，约50-120字
6. 只输出JSON格式：{{"0": "描述文字", "4": "描述文字", ...}}，key是表格idx的字符串

表格列表：
{tables_str}

请输出JSON：'''

    payload = {
        "model": "Claude Sonnet 4.6",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8000
    }
    
    cmd = [
        "curl", "-s", "-X", "POST", URL,
        "-H", f"Authorization: Bearer {API_KEY}",
        "-H", "anthropic-version: 2023-06-01",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload, ensure_ascii=False)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        resp = json.loads(result.stdout)
        if "content" in resp and len(resp["content"]) > 0:
            text = resp["content"][0]["text"]
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                json_str = text[start:end+1]
                batch_desc = json.loads(json_str)
                for k, v in batch_desc.items():
                    all_descriptions[k] = v.strip()
                print(f"  Got {len(batch_desc)} descriptions", flush=True)
            else:
                print(f"  No JSON found, using fallback", flush=True)
                for t in batch:
                    all_descriptions[str(t["idx"])] = generate_fallback(t)
        else:
            print(f"  API error: {resp.get('error', resp)}", flush=True)
            for t in batch:
                all_descriptions[str(t["idx"])] = generate_fallback(t)
    except Exception as e:
        print(f"  Error: {e}, using fallback", flush=True)
        for t in batch:
            all_descriptions[str(t["idx"])] = generate_fallback(t)
    
    time.sleep(2)

# Save results
with open("descriptions.json", "w") as f:
    json.dump(all_descriptions, f, ensure_ascii=False, indent=2)

print(f"\n=== Total descriptions: {len(all_descriptions)} ===")
for k in sorted(all_descriptions.keys(), key=int):
    print(f"  Table {k}: {all_descriptions[k][:80]}...")
