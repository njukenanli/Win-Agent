from argparse import ArgumentParser
import os
import time

def safe_read(path):
    '''
    write file ops from the host need time to sync to container.
    '''
    for trial in range(3):
        try:
            with open(os.path.abspath(path), encoding="utf-8") as f:
                s = f.read()
                return s
        except:
            time.sleep(16)
            continue
    raise FileNotFoundError(path)

parser = ArgumentParser()
parser.add_argument("--path_file", type=str)
parser.add_argument("--old_file", type=str)
parser.add_argument("--new_file", type=str)
parser.add_argument("--output_file", type=str)
args = parser.parse_args()

path = safe_read(args.path_file)

old_string = safe_read(args.old_file)

new_string = safe_read(args.new_file)

def string_replace(path, old_string, new_string):
    if not os.path.isfile(path):
        return f"{path} is not found or is directory. If is directory, string_replace is to edit file."
    
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        import traceback
        return f"{e}\n{traceback.format_exc()}\nPath not found or is directory or you do not have permission. If is directory, string_replace is to edit file. If you do not have permission please run shell commands to change permission."
    
    matches = content.count(old_string) 
    if matches > 1:
        return "old_string has multiple matches in the target file, so string replace is not performed. your old_string should have a wider span to be more specific."
    if matches == 0:
        return "old_string not found in the target file."
    content = content.replace(old_string, new_string)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    
    start = content.find(new_string)
    end = start + len(new_string)
    # new string range is [start, end)
    pre = content[:start].splitlines()
    med = new_string.splitlines()
    post = content[end:].splitlines() if end < len(content) else []
    start = max(len(pre) - 15, 0)
    end = min(len(pre) + len(med) + 15 , len(pre) + len(med) + len(post))
    display = content.splitlines()[start: end]
    display = [f"{i+start+1}|{line}" for i, line in enumerate(display)]
    return "string replace successful, new file content:\n" + "\n".join(display)



res = string_replace(path, old_string, new_string)
with open(os.path.abspath(args.output_file), "w", encoding="utf-8") as f:
    f.write(res)
