import requests

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


def get_dataset_list(BASE_URL):
    """
    list of datasets
    """
    print('getting the list of dataset')
    response = requests.get(f"{BASE_URL}/dataset/list")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch task status: {response.status_code}, {response.text}")
        return None

def get_dataset_id_list(BASE_URL):
    """
    list of datasets
    """
    print('getting the list of dataset')
    response = requests.get(f"{BASE_URL}/dataset/id-list")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch task status: {response.status_code}, {response.text}")
        return None

def post_dataset(BASE_URL, data):
    """
    post a dataset
    """
    response = requests.post(
        f"{BASE_URL}/dataset/new",
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