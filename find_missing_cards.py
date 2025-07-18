import os

def find_folders_without_png(base_dir):
    folders_without_png = []

    # Walk through all directories and subdirectories in base_dir
    for root, dirs, files in os.walk(base_dir):
        # Check if the current directory name contains the word "christmas" (case-insensitive)
        #if "christmas" in root.lower():
        #    continue

        # Check if any file in the current directory has a .png extension
        if not any(file.lower().endswith('.png') for file in files):
            # Collect the current directory name if no .png files are found
            folders_without_png.append(root)

    # Sort the list of directories alphabetically
    folders_without_png.sort()

    # Print the sorted list of directories
    for folder in folders_without_png:
        print(folder)

if __name__ == "__main__":
    # Set the base directory to './library'
    base_directory = './library'
    find_folders_without_png(base_directory)
