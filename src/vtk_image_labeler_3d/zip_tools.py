import zipfile
import os

def unzip_to_folder(zip_path, extract_to_folder):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.namelist():
            target_path = os.path.join(extract_to_folder, member)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # Overwrite if exists
            with open(target_path, 'wb') as f:
                f.write(zip_ref.read(member))

    print(f"Unzipped to: {extract_to_folder}")