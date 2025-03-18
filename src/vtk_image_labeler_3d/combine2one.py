import os
from pathlib import Path

# Specify the directory containing the .py files
directory = ""

# File to save the combined content
output_file = "_all.txt"

# Create or overwrite the output file
with open(output_file, "w", encoding="utf-8") as outfile:
    for file in Path(directory).glob("*.py"):  # Find all .py files in the directory
        with open(file, "r", encoding="utf-8") as infile:
            outfile.write(f"# Start of {file.name}\n")  # Optionally add file header
            outfile.write(infile.read())  # Write the file's content
            outfile.write("\n\n")  # Add a blank line between files

print(f"Combined content saved to {output_file}")
