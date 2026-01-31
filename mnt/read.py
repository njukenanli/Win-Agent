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
parser.add_argument("--start", type=int, default=-1)
parser.add_argument("--end", type=int, default=-1)
parser.add_argument("--output_file", type=str)
args = parser.parse_args()

path = safe_read(args.path_file)

def view(path, start, end):
    if not os.path.exists(path):
        return f"{path} not found"
    
    with open(path, encoding="utf-8") as f:
        content_list = f.read().splitlines()
    if start > len(content_list):
        return f"start line number > max line number. there are {len(content_list)} lines in the file."
    base = 1
    if start >= 0 and start <= end:
        content_list = content_list[start-1 : end]
        base = start 
    with_number = [f"{i+base}|{line}" for i, line in enumerate(content_list)]
    return "\n".join(with_number)

res = view(path, args.start, args.end)
with open(os.path.abspath(args.output_file), "w", encoding="utf-8") as f:
    f.write(res)
