import requests, os, re, json

class ServerError(Exception):
    """Custom exception for server errors."""
    pass

def get_ping(BASE_URL):
    """
    Ping the server and return the response.
    """
    url = f"{BASE_URL}/ping"
    print(f'pinging the server at {url}')
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_message = f"Failed to ping server: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)  # Raise a custom exception for server errors
    except requests.exceptions.RequestException as e:
        # Handle network-related errors (e.g., connection issues)
        print(f"An error occurred while pinging the server: {e}")
        raise  # Re-raise the exception to forward it

def get_dataset_json_list(BASE_URL):
    """
    list of datasets
    """
    print('getting the list of dataset')
    response = requests.get(f"{BASE_URL}/dataset_json/list")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch task status: {response.status_code}, {response.text}")
        return None

def get_dataset_json_id_list(BASE_URL):
    """
    list of datasets
    """
    print('getting the list of dataset')
    response = requests.get(f"{BASE_URL}/dataset_json/id-list")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch task status: {response.status_code}, {response.text}")
        return None

def get_dataset_image_name_list(BASE_URL, dataset_id):
    """
    Fetch the list of image and label file names for a given dataset.
    """
    print(f'Getting the image name list for dataset: {dataset_id}')
    params = {"dataset_id": dataset_id}
    response = requests.get(f"{BASE_URL}/dataset/image_name_list", params=params)

    if response.status_code == 200:
        return response.json()
    else:
        error_message = f"Failed to fetch image name list: {response.status_code}, {response.text}"
        print(error_message)
        raise ServerError(error_message)  # Raise a custom exception for server errors
    
    

def download_dataset_images_and_labels(BASE_URL, dataset_id, images_for, num, out_dir):
    url = f"{BASE_URL}/dataset/get_image_and_labels"
    params = {
        "dataset_id": dataset_id,
        "images_for": images_for,
        "num": num
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        result = response.json()
        print("Image filename:", result["base_image_filename"])
        print("Label filename:", result["labels_filename"])
        print("Image download URL:", result["base_image_url"])
        print("Label download URL:", result["labels_url"])

        if not os.path.exists(out_dir):
            print(f"Creating out_dir: {out_dir}")
            os.makedirs(out_dir)

        # Download base image
        base_image_path = os.path.join(out_dir, result['base_image_filename'])
        img_response = requests.get(f"{BASE_URL}{result['base_image_url']}")
        if img_response.status_code == 200:
            print(f"Saving base image to: {base_image_path}")
            with open(base_image_path, "wb") as f:
                f.write(img_response.content)
        else:
            raise Exception(f"Failed to download base image: {img_response.status_code}")

        # Download label image
        label_image_path = os.path.join(out_dir, result['labels_filename'])
        lbl_response = requests.get(f"{BASE_URL}{result['labels_url']}")
        if lbl_response.status_code == 200:
            print(f"Saving label image to: {label_image_path}")
            with open(label_image_path, "wb") as f:
                f.write(lbl_response.content)
        else:
            raise Exception(f"Failed to download label image: {lbl_response.status_code}")

        return {
            'image_and_labels': result,
            'downloaded_base_image_path': base_image_path,
            'downloaded_labels_image_path': label_image_path,
        }

    else:
        raise Exception(f"Failed to fetch metadata: {response.status_code}, {response.text}")
    
def post_dataset_json(BASE_URL, data):
    """
    post a dataset
    """
    response = requests.post(
        f"{BASE_URL}/dataset_json/new",
        json=data,  # Task input as JSON payload
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to add a dataset: {response.status_code}, {response.text}")
        return None

def post_image_and_labels(BASE_URL, dataset_id, images_for, image_path, labels_path):
    # Required metadata
    # dataset_id = "Dataset935_Test1"
    # images_for = "train"  # Must be "train" or "test"
    url = f"{BASE_URL}/dataset/add_image_and_labels"

    try:
        # Open files safely using 'with' to avoid leaks
        with open(image_path, "rb") as img_file, open(labels_path, "rb") as lbl_file:
            files = {
                "base_image": img_file,
                "labels": lbl_file,
            }
            
            data = {
                "dataset_id": dataset_id,
                "images_for": images_for,  # train or test
            }
                
            response = requests.post(url, files=files, data=data)

        # Print response with error handling
        if response.status_code == 200:
            reseponse_data = response.json()
            print("Success:", reseponse_data)
            return reseponse_data
        else:
            error_message = f"Failed to ping server: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)  # Raise a custom exception for server errors
    except requests.exceptions.RequestException as e:
        # Handle network-related errors (e.g., connection issues)
        print(f"An error occurred while pushing images to the server: {e}")
        raise  # Re-raise the exception to forward it


def update_image_and_labels(BASE_URL, dataset_id, images_for, num, image_path, labels_path):
    # Required metadata
    # dataset_id = "Dataset935_Test1"
    # images_for = "train"  # Must be "train" or "test"
    url = f"{BASE_URL}/dataset/update_image_and_labels"

    try:
        # Open files safely using 'with' to avoid leaks
        with open(image_path, "rb") as img_file, open(labels_path, "rb") as lbl_file:
            files = {
                "base_image": img_file,
                "labels": lbl_file,
            }
            
            data = {
                "dataset_id": dataset_id,
                "images_for": images_for,  # train or test
                "num": num
            }
                
            response = requests.put(url, files=files, data=data)

        # Print response with error handling
        if response.status_code == 200:
            reseponse_data = response.json()
            print("Success:", reseponse_data)
            return reseponse_data
        else:
            error_message = f"Failed to ping server: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)  # Raise a custom exception for server errors
    except requests.exceptions.RequestException as e:
        # Handle network-related errors (e.g., connection issues)
        print(f"An error occurred while pushing images to the server: {e}")
        raise  # Re-raise the exception to forward it

    
def delete_image_and_labels(BASE_URL, dataset_id, images_for, num):
    # Required metadata
    # dataset_id = "Dataset935_Test1"
    # images_for = "train"  # Must be "train" or "test"
    url = f"{BASE_URL}/dataset/delete_image_and_labels"

    try:
        # Use query parameters for DELETE
        params = {
            "dataset_id": dataset_id,
            "images_for": images_for,
            "num": num
        }
            
        response = requests.delete(url, params=params)

        # Print response with error handling
        if response.status_code == 200:
            reseponse_data = response.json()
            print("Success:", reseponse_data)
            return reseponse_data
        else:
            error_message = f"Failed to ping server: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)  # Raise a custom exception for server errors
    except requests.exceptions.RequestException as e:
        # Handle network-related errors (e.g., connection issues)
        print(f"An error occurred while pushing images to the server: {e}")
        raise  # Re-raise the exception to forward it