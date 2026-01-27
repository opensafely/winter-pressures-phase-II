import os
import shutil

# Define source and destination directories
source_dir = 'output/practice_measures_resp_yearly'
dest_dir = 'output/practice_measures_resp'

# Ensure destination directory exists
os.makedirs(dest_dir, exist_ok=True)

# Move all files from source to destination
for filename in os.listdir(source_dir):
    source_file = os.path.join(source_dir, filename)
    if os.path.isfile(source_file):
        name, ext = os.path.splitext(filename)
        if ext == '.arrow':
            new_filename = f"{name}_yearly{ext}"
        else:
            new_filename = filename
        dest_file = os.path.join(dest_dir, new_filename)
        shutil.move(source_file, dest_file)
        print(f"Moved {filename} to {new_filename} in {dest_dir}")

print("All files moved successfully.")
