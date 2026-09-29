import json

path = r'C:\Users\huxley\.gemini\antigravity-ide\brain\deb08045-5a14-42e7-91fc-5f77f561a910\.system_generated\logs\transcript.jsonl'
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        content = str(data.get('content', ''))
        if '퉁치기' in content or '자전거래' in content or '상계' in content:
            idx = data.get('step_index')
            role = data.get('type')
            print(f"Step {idx} [{role}]: {content[:200]}...")
