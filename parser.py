import os
import vpk
import vdf
import zipfile
import py7zr
import rarfile
import tempfile
import shutil

def parse_mission_file(content):
    try:
        data = vdf.loads(content)
        # Handle cases where the root key is capitalized differently
        mission_key = next((k for k in data.keys() if k.lower() == "mission"), None)
        if not mission_key:
            return None
        return data[mission_key]
    except Exception as e:
        print(f"Failed to parse mission vdf: {e}")
        return None

def extract_tokens(content):
    tokens = {}
    try:
        data = vdf.loads(content)
        lang_key = next((k for k in data.keys() if k.lower() == "lang"), None)
        if lang_key:
            tokens_key = next((k for k in data[lang_key].keys() if k.lower() == "tokens"), None)
            if tokens_key:
                for k, v in data[lang_key][tokens_key].items():
                    tokens[k.lower()] = v
    except Exception as e:
        pass
    return tokens

def get_localized_string(text, tokens):
    if not text:
        return "Unknown"
    if text.startswith("#"):
        key = text[1:].lower()
        return tokens.get(key, text)
    return text

def decode_content(raw_bytes):
    # Try multiple encodings
    for encoding in ['utf-8-sig', 'utf-16', 'utf-8', 'gbk']:
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    # Fallback to ignore
    return raw_bytes.decode('utf-8', errors='ignore')

def parse_vpk(file_path, target_lang="schinese"):
    # Try to open vpk
    try:
        pak = vpk.open(file_path)
    except Exception as e:
        print(f"Failed to open VPK {file_path}: {e}")
        return []
    
    mission_files = []
    resource_files = []
    
    for filepath in pak:
        if filepath.startswith("missions/") and filepath.endswith(".txt"):
            mission_files.append(filepath)
        elif filepath.startswith("resource/") and filepath.endswith(".txt"):
            resource_files.append(filepath)
            
    if not mission_files:
        return []

    # Read tokens from all resources, using dynamic language priority
    tokens = {}
    
    # Priority of languages: requested lang -> english -> any other
    priorities = [target_lang, "english"]
    
    # 尝试读取对应语言文件
    for lang in reversed(priorities):
        for res_file in resource_files:
            # 兼容带有 l4d360ui_ 前缀的情况
            if lang in res_file.lower():
                try:
                    f = pak.get_file(res_file)
                    content = decode_content(f.read())
                    tokens.update(extract_tokens(content))
                except Exception as e:
                    print(f"Error reading resource {res_file}: {e}")
                    
    results = []
    
    for mission_file in mission_files:
        try:
            f = pak.get_file(mission_file)
            content = decode_content(f.read())
            mission_data = parse_mission_file(content)
            
            if not mission_data:
                continue
                
            display_title_raw = mission_data.get("DisplayTitle", "Unknown Campaign")
            campaign_name = get_localized_string(display_title_raw, tokens)
            
            modes_key = next((k for k in mission_data.keys() if k.lower() == "modes"), None)
            if not modes_key:
                continue
                
            modes = mission_data[modes_key]
            # Try coop first, then campaign, then whatever is available
            coop_key = next((k for k in modes.keys() if k.lower() == "coop"), None)
            if not coop_key:
                coop_key = next((k for k in modes.keys() if k.lower() == "campaign"), None)
            if not coop_key and len(modes) > 0:
                coop_key = list(modes.keys())[0]
                
            if not coop_key:
                continue
                
            chapters = modes[coop_key]
            
            # chapters is a dict like {"1": {...}, "2": {...}}
            # Filter out non-numeric keys if any
            chapter_items = []
            for k, v in chapters.items():
                if isinstance(v, dict) and "Map" in v:
                    try:
                        chapter_items.append((int(k), v))
                    except ValueError:
                        pass
                        
            chapter_items.sort(key=lambda x: x[0])
            total_chapters = len(chapter_items)
            
            for index, (_, chapter_data) in enumerate(chapter_items):
                map_code = chapter_data.get("Map")
                display_name_raw = chapter_data.get("DisplayName", chapter_data.get("Title", f"Chapter {index+1}"))
                chapter_name = get_localized_string(display_name_raw, tokens)
                
                results.append({
                    "map_code": map_code,
                    "campaign_name": campaign_name,
                    "chapter_name": chapter_name,
                    "chapter_num": index + 1,
                    "total_chapters": total_chapters
                })
                
        except Exception as e:
            print(f"Error processing mission {mission_file}: {e}")
            
    return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        res = parse_vpk(sys.argv[1])
        for r in res:
            print(f"{r['map_code']}: {r['campaign_name']}: {r['chapter_name']} [{r['chapter_num']}/{r['total_chapters']}]")
