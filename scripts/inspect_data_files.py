import os

files = [
    "docs/内部参考/数据资料/DMP_F_MID_ORG_TREE_20250630.txt",
    "docs/内部参考/数据资料/ods_g_c_dim_date_20250630.txt"
]

for f_path in files:
    print(f"--- Inspecting {f_path} ---")
    if not os.path.exists(f_path):
        print("File not found.")
        continue
        
    try:
        with open(f_path, 'r', encoding='utf-8') as f:
            line = f.readline()
            print(f"Raw repr: {repr(line)}")
            # Split by common delimiters to see count
            print(f"Split by \\x1b: {len(line.split(chr(27)))}")
            print(f"Split by \\t: {len(line.split(chr(9)))}")
            print(f"Split by ,: {len(line.split(','))}")
    except Exception as e:
        print(f"Error reading file: {e}")
