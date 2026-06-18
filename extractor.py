import json
import re
import os

log_path = r"C:\Users\bhask\.gemini\antigravity\brain\18c93098-e4a2-4f9d-bd26-b6782a760dd5\.system_generated\logs\transcript_full.jsonl"

def extract_files():
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if "invoke_subagent" in line and "=== FILE" in line:
                try:
                    data = json.loads(line)
                    if "tool_calls" in data:
                        for call in data["tool_calls"]:
                            if call.get("name") == "invoke_subagent":
                                subagents_data = call.get("args", {}).get("Subagents", [])
                                if isinstance(subagents_data, str):
                                    subagents = json.loads(subagents_data)
                                else:
                                    subagents = subagents_data
                                for sub in subagents:
                                    prompt = sub.get("Prompt", "")
                                    if "=== FILE" in prompt:
                                        # Parse prompt
                                        # format is:
                                        # === FILE 1: path ===
                                        # ```python
                                        # code
                                        # ```
                                        parts = prompt.split("=== FILE")
                                        for part in parts[1:]:
                                            lines = part.strip().split("\n")
                                            # First line is something like " 1: d:\path\to\file.py ==="
                                            header = lines[0]
                                            path_match = re.search(r':\s*(.+?)\s*===', header)
                                            if not path_match:
                                                continue
                                            filepath = path_match.group(1).strip()
                                            
                                            # Find content between ```
                                            content = []
                                            in_block = False
                                            for l in lines[1:]:
                                                if l.startswith("```"):
                                                    if in_block:
                                                        break
                                                    else:
                                                        in_block = True
                                                elif in_block:
                                                    content.append(l)
                                            
                                            full_content = "\n".join(content)
                                            if full_content and filepath:
                                                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                                                # Only write if it doesn't exist or is empty
                                                if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                                                    with open(filepath, 'w', encoding='utf-8') as out:
                                                        out.write(full_content)
                                                    print(f"Created {filepath}")
                except Exception as e:
                    print(f"Error parsing line: {e}")

if __name__ == "__main__":
    extract_files()
