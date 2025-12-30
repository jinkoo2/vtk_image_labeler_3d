import requests, os, re, json

class ServerError(Exception):
    """Custom exception for server errors."""
    pass

test_user = {
  "email": "test@email.com",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGVtYWlsLmNvbSIsImV4cCI6MTc5NTg5ODc4M30.Zu_fZ4T1pq78vs-XkrYAJbUGpQPwWQjKL0bQMxDLrNo"
}

def get_ping(BASE_URL, timeout_seconds=10):
    """
    Ping the server and return the response with timeout handling.
    """
    url = f"{BASE_URL}/status/ping"
    print(f'Pinging the server at {url}')
    
    # The header must follow the format: Authorization: Bearer <TOKEN>
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout_seconds)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_message = f"Failed to ping server: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while pinging the server: {e}")
        raise

def get_dataset_json_list(BASE_URL, timeout_seconds=10): 
    """
    List of datasets with timeout handling
    """
    print('Getting the list of dataset')
    
    # The header must follow the format: Authorization: Bearer <TOKEN>
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }

    try:
        response = requests.get(f"{BASE_URL}/datasets/list", 
                                headers=headers,
                                timeout=timeout_seconds)
        if response.status_code == 200:
            return response.json()
        else:
            error_message = f"Failed to fetch task status: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise 
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        raise 

def get_dataset_json_id_list(BASE_URL, timeout_seconds=10):
    """
    List of dataset IDs with timeout handling.
    """
    print('Getting the list of dataset IDs')

     # The header must follow the format: Authorization: Bearer <TOKEN>
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }

    try:
        response = requests.get(f"{BASE_URL}/datasets/id-list", 
                                headers=headers,
                                timeout=timeout_seconds)
        if response.status_code == 200:
            return response.json()
        else:
            error_message = f"Failed to fetch task status: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching dataset ID list: {e}")
        raise

def get_dataset_image_name_list(BASE_URL, dataset_id, timeout_seconds=10):
    """
    Fetch the list of image and label file names for a given dataset with timeout handling.
    """
    print(f'Getting the image name list for dataset: {dataset_id}')
    params = {"dataset_id": dataset_id}
    
    # The header must follow the format: Authorization: Bearer <TOKEN>
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }

    try:
        response = requests.get(f"{BASE_URL}/datasets/image_name_list", 
                                params=params, 
                                headers= headers,
                                timeout=timeout_seconds)
        if response.status_code == 200:
            return response.json()
        else:
            error_message = f"Failed to fetch image name list: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching image name list: {e}")
        raise
        

def download_dataset_images_and_labels(BASE_URL, dataset_id, images_for, num, out_dir):
    url = f"{BASE_URL}/datasets/get_image_and_labels"
    params = {
        "dataset_id": dataset_id,
        "images_for": images_for,
        "num": num
    }
    # The header must follow the format: Authorization: Bearer <TOKEN>
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }

    response = requests.get(url, 
                            params=params,
                            headers=headers
                            )

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
        img_response = requests.get(f"{BASE_URL}{result['base_image_url']}", 
                                    headers={
                                    "Authorization": f"Bearer {test_user['token']}"
                                })
        if img_response.status_code == 200:
            print(f"Saving base image to: {base_image_path}")
            with open(base_image_path, "wb") as f:
                f.write(img_response.content)
        else:
            raise Exception(f"Failed to download base image: {img_response.status_code}")

        # Download label image
        label_image_path = os.path.join(out_dir, result['labels_filename'])
        lbl_response = requests.get(f"{BASE_URL}{result['labels_url']}",
                                    headers={
                                    "Authorization": f"Bearer {test_user['token']}"
                                })
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
        f"{BASE_URL}/datasets/new",
        json=data,  # Task input as JSON payload
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {test_user['token']}"
            }
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
    url = f"{BASE_URL}/datasets/add_image_and_labels"

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
                
            response = requests.post(url, 
                                     files=files, 
                                     headers={
                                            "Authorization": f"Bearer {test_user['token']}"
                                     },
                                     data=data)

        # Print response with error handling
        if response.status_code == 200:
            reseponse_data = response.json()
            print("Success:", reseponse_data)
            return reseponse_data
        else:
            error_message = f"Failed posting image and label: {response.status_code}, {response.text}"
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
    url = f"{BASE_URL}/datasets/update_image_and_labels"

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
                
            response = requests.put(url, 
                                    files=files, 
                                    headers={
                                           "Authorization": f"Bearer {test_user['token']}"
                                    },
                                    data=data)

        # Print response with error handling
        if response.status_code == 200:
            reseponse_data = response.json()
            print("Success:", reseponse_data)
            return reseponse_data
        else:
            error_message = f"Failed updating image and label pair: {response.status_code}, {response.text}"
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
    url = f"{BASE_URL}/datasets/delete_image_and_labels"

    try:
        # Use query parameters for DELETE
        params = {
            "dataset_id": dataset_id,
            "images_for": images_for,
            "num": num
        }
            
        response = requests.delete(url, 
                                   headers={
                                       "Authorization": f"Bearer {test_user['token']}"
                                       },
                                   params=params)

        # Print response with error handling
        if response.status_code == 200:
            reseponse_data = response.json()
            print("Success:", reseponse_data)
            return reseponse_data
        else:
            error_message = f"Failed deleting image and label pair: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)  # Raise a custom exception for server errors
    except requests.exceptions.RequestException as e:
        # Handle network-related errors (e.g., connection issues)
        print(f"An error occurred while pushing images to the server: {e}")
        raise  # Re-raise the exception to forward it



def test_post_predictions_zip():
    url = "http://127.0.0.1:8000/predictions_zip"

    dataset_id = "Dataset847_FourCirclesOnJawCalKv2"
    requester_id = "tester_001"
    image_id_list = "image0|image1"

    zip_dir = os.path.join(os.path.dirname(__file__), "_test_images/temp")
    images_dir = os.path.join(os.path.dirname(__file__), "_test_images/predictions")
    zip_path = os.path.join(zip_dir, 'images.zip')

    os.makedirs(zip_dir, exist_ok=True)
    zip_mha_files(images_dir, zip_path)

    extra_fields = {
        "notes": "This is a test",
        "priority": "high",
        "name": "jinkoo kim",
        "inst": "stony brook"
    }

    with open(zip_path, "rb") as zip_file:
        form_data = {
            "dataset_id": dataset_id,
            "requester_id": requester_id,
            "image_id_list": image_id_list,
            **extra_fields
        }
        files = {
            "images_zip": ("images.zip", zip_file, "application/zip")
        }

        response = requests.post(url, data=form_data, files=files, headers={
            "Authorization": f"Bearer {test_user['token']}"
        }   )

    if response.status_code == 200:
        print("Request succeeded:", response.json())
    else:
        print(f"Error {response.status_code}: {response.text}")

def test_post_predictions():
    url = "http://127.0.0.1:8000/predictions"

    dataset_id = "Dataset847_FourCirclesOnJawCalKv2"
    requester_id = "tester_001"
    image_id = "image0"

    
    images_dir = os.path.join(os.path.dirname(__file__), "_test_images/predictions")
    image_path = os.path.join(images_dir, '0.mha')

    extra_fields = {
        "notes": "This is a test for 1 image prediction",
        "priority": "high",
        "name": "jinkoo kim",
        "inst": "stony brook"
    }

    with open(image_path, "rb") as image_file:
        form_data = {
            "dataset_id": dataset_id,
            "requester_id": requester_id,
            "image_id": image_id,
            **extra_fields
        }
        files = {
            "image": image_file
        }

        response = requests.post(url, data=form_data, files=files, headers={
            "Authorization": f"Bearer {test_user['token']}"
        })

    if response.status_code == 200:
        print("Request succeeded:", response.json())
    else:
        print(f"Error {response.status_code}: {response.text}")

def get_prediction_list(BASE_URL, dataset_id):
    print(f'getting prediciont list for {dataset_id}')

    url = f"{BASE_URL}/predictions/list"
    params = {"dataset_id": dataset_id}

    try:
        response = requests.get(url, 
                                params=params,
                                headers={
                                    "Authorization": f"Bearer {test_user['token']}"
                                })

        if response.status_code == 200:
            data = response.json()
            print("Prediction requests:", data)
            return data
        else:
            error_message = f"GET failed: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching prediction status: {e}")
        raise


def post_image_for_prediction(BASE_URL, dataset_id, image_path, requester_id, image_id, req_metadata):

    url = f"{BASE_URL}/predictions/predict"

    print("request metadata:", req_metadata)
    
    req_metadata['requester_id'] = requester_id

    try:
       with open(image_path, "rb") as image_file:
        form_data = {
            "dataset_id": dataset_id,
            "image_id": image_id,
            **req_metadata
        }
        files = {
            "image": image_file
        }

        response = requests.post(url, 
                                 data=form_data, 
                                 files=files,
                                 headers={
                                     "Authorization": f"Bearer {test_user['token']}"
                                 })

        # Print response with error handling
        if response.status_code == 200:
            reseponse_data = response.json()
            print("Success:", reseponse_data)
            return reseponse_data
        else:
            error_message = f"Failed to post image for prediction: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)  # Raise a custom exception for server errors
    except requests.exceptions.RequestException as e:
        # Handle network-related errors (e.g., connection issues)
        print(f"An error occurred while pushing images to the server: {e}")
        raise  # Re-raise the exception to forward it

def delete_prediction(BASE_URL, dataset_id, req_id):
    url = f"{BASE_URL}/predictions/delete"
    params = {"dataset_id": dataset_id, "req_id": req_id}
    print(f"nnunet_service.delete_prediction: url={url}, params={params}")
    
    try:
        response = requests.delete(url, 
                                params=params,
                                headers={"Authorization": f"Bearer {test_user['token']}"})

        if response.status_code == 200:
            print("Delete successful:", response.json())
            return response.json()
        else:
            error_message = f"DELETE failed: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while deleting prediction request: {e}")
        raise


def download_prediction_images_and_labels(BASE_URL, dataset_id, req_id, image_number, out_dir):
    # 1. Get metadata and download URL
    meta_url = f"{BASE_URL}/predictions/image_and_label_metadata"
    meta_params = {
        "dataset_id": dataset_id,
        "req_id": req_id,
        "image_number": image_number
    }
    meta_response = requests.get(meta_url, params=meta_params, headers={
        "Authorization": f"Bearer {test_user['token']}"
    })

    if meta_response.status_code != 200:
        raise Exception(f"Failed to fetch metadata: {meta_response.status_code}, {meta_response.text}")

    metadata = meta_response.json()
    image_names = metadata.get("image_names", [])
    label_name = metadata.get("label_name", "")
    download_url = f"{BASE_URL}{metadata.get('download_url')}"

    print("Image files:", image_names)
    print("Label file:", label_name)
    print("Download URL:", download_url)

    # 2. Download ZIP
    if not os.path.exists(out_dir):
        print(f"Creating output directory: {out_dir}")
        os.makedirs(out_dir)

    zip_filename = f"{req_id}_image_{image_number}.zip"
    zip_path = os.path.join(out_dir, zip_filename)

    zip_response = requests.get(download_url,
                                headers={
                                    "Authorization": f"Bearer {test_user['token']}"
                                })
    if zip_response.status_code == 200:
        print(f"Saving ZIP to: {zip_path}")
        with open(zip_path, "wb") as f:
            f.write(zip_response.content)
    else:
        raise Exception(f"Failed to download ZIP file: {zip_response.status_code}")

    return {
        "image_names": image_names,
        "label_name": label_name,
        "zip_path": zip_path
    }

def post_plan_and_preprocess_run(BASE_URL, dataset_id, timeout_seconds=10):
    """
    Submit a nnU-Net plan & preprocess job.
    
    This endpoint enqueues a job to plan and preprocess a dataset. The output directory
    is automatically set to `nnUNet_preprocessed/{dataset_id}`.
    
    Args:
        BASE_URL: Base URL of the API server
        dataset_id: The full dataset identifier (e.g., "Dataset015_CBCTBladder")
        timeout_seconds: Request timeout in seconds (default: 10)
    
    Returns:
        Response JSON containing job_id, dataset_id, and number_of_jobs_ahead
    
    Raises:
        ServerError: If the request fails
        requests.exceptions.RequestException: For network errors
    """
    url = f"{BASE_URL}/plan_and_preprocess/run"
    print(f'Submitting plan and preprocess job for dataset: {dataset_id}')
    
    # The header must follow the format: Authorization: Bearer <TOKEN>
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }
    
    # Form data for application/x-www-form-urlencoded
    data = {
        "dataset_id": dataset_id
    }
    
    try:
        response = requests.post(url, 
                                data=data,
                                headers=headers,
                                timeout=timeout_seconds)
        
        if response.status_code == 200:
            response_data = response.json()
            print("Success:", response_data)
            return response_data
        else:
            error_message = f"Failed to submit plan and preprocess job: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while submitting plan and preprocess job: {e}")
        raise

def get_plan_and_preprocess_job_status(BASE_URL, job_id, timeout_seconds=10):
    """
    Check the RQ job status and progress for plan & preprocess jobs.
    
    Args:
        BASE_URL: Base URL of the API server
        job_id: The RQ job ID returned from the `/run` endpoint
        timeout_seconds: Request timeout in seconds (default: 10)
    
    Returns:
        Response JSON containing job status, progress, queue position, and result/error if available
    
    Raises:
        ServerError: If the request fails
        requests.exceptions.RequestException: For network errors
    """
    url = f"{BASE_URL}/plan_and_preprocess/job_status/{job_id}"
    print(f'Checking plan and preprocess job status for job_id: {job_id}')
    
    # The header must follow the format: Authorization: Bearer <TOKEN>
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }
    
    try:
        response = requests.get(url,
                               headers=headers,
                               timeout=timeout_seconds)
        
        if response.status_code == 200:
            response_data = response.json()
            print("Job status:", response_data)
            return response_data
        else:
            error_message = f"Failed to get job status: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while checking job status: {e}")
        raise

def get_preprocessed_summary(BASE_URL, dataset_id, timeout_seconds=10):
    """
    Get the preprocessed summary for a dataset.
    
    Loads and returns the `preprocess_summary.json` file from the preprocessed directory
    for the given dataset. If the file is not found, returns an empty object.
    
    Args:
        BASE_URL: Base URL of the API server
        dataset_id: The full dataset identifier (e.g., "Dataset015_CBCTBladder")
        timeout_seconds: Request timeout in seconds (default: 10)
    
    Returns:
        Response JSON containing the preprocessed summary data
    
    Raises:
        ServerError: If the request fails
        requests.exceptions.RequestException: For network errors
    """
    url = f"{BASE_URL}/plan_and_preprocess/results/preprocess_summary"
    print(f'Getting preprocessed summary for dataset: {dataset_id}')
    
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }
    
    params = {
        "dataset_id": dataset_id
    }
    
    try:
        response = requests.get(url,
                               params=params,
                               headers=headers,
                               timeout=timeout_seconds)
        
        if response.status_code == 200:
            response_data = response.json()
            print("Preprocessed summary:", response_data)
            return response_data
        else:
            error_message = f"Failed to get preprocessed summary: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting preprocessed summary: {e}")
        raise

def get_preprocessed_files(BASE_URL, dataset_id, timeout_seconds=10):
    """
    Get list of available preprocessed result files for a dataset.
    
    Returns the names of files that exist in the preprocessed directory:
    - `preprocess_summary.json` - Preprocessing execution summary
    - `nnUNetPlans.json` - nnU-Net planning configuration
    - `dataset_fingerprint.json` - Dataset fingerprint information
    - `preprocess.log` - Preprocessing log file
    
    Only files that exist will be included in the response.
    
    Args:
        BASE_URL: Base URL of the API server
        dataset_id: The full dataset identifier (e.g., "Dataset984_Test")
        timeout_seconds: Request timeout in seconds (default: 10)
    
    Returns:
        Response JSON containing a list of file names that are available
    
    Raises:
        ServerError: If the request fails
        requests.exceptions.RequestException: For network errors
    """
    url = f"{BASE_URL}/plan_and_preprocess/results/files"
    print(f'Getting preprocessed files list for dataset: {dataset_id}')
    
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }
    
    params = {
        "dataset_id": dataset_id
    }
    
    try:
        response = requests.get(url,
                               params=params,
                               headers=headers,
                               timeout=timeout_seconds)
        
        if response.status_code == 200:
            response_data = response.json()
            print("Preprocessed files:", response_data)
            return response_data
        else:
            error_message = f"Failed to get preprocessed files: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting preprocessed files: {e}")
        raise

def get_preprocessed_file_content(BASE_URL, dataset_id, file_name, timeout_seconds=10):
    """
    Get the content of a specific preprocessed result file for a dataset.
    
    Returns the contents of one of the allowed files:
    - `preprocess_summary.json` - Preprocessing execution summary (returns JSON)
    - `nnUNetPlans.json` - nnU-Net planning configuration (returns JSON)
    - `dataset_fingerprint.json` - Dataset fingerprint information (returns JSON)
    - `preprocess.log` - Preprocessing log file (returns text)
    
    Args:
        BASE_URL: Base URL of the API server
        dataset_id: The full dataset identifier (e.g., "Dataset984_Test")
        file_name: The name of the file to read (must be one of the allowed files)
        timeout_seconds: Request timeout in seconds (default: 10)
    
    Returns:
        Response JSON containing the file content. JSON files are parsed and returned as objects,
        log files are returned as strings.
    
    Raises:
        ServerError: If the request fails
        requests.exceptions.RequestException: For network errors
    """
    url = f"{BASE_URL}/plan_and_preprocess/results/file_content"
    print(f'Getting preprocessed file content for dataset: {dataset_id}, file: {file_name}')
    
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }
    
    params = {
        "dataset_id": dataset_id,
        "file_name": file_name
    }
    
    try:
        response = requests.get(url,
                               params=params,
                               headers=headers,
                               timeout=timeout_seconds)
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"File content for {file_name}:", response_data)
            return response_data
        else:
            error_message = f"Failed to get file content: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting file content: {e}")
        raise

def get_preprocessed_results_details(BASE_URL, dataset_id, timeout_seconds=10):
    """
    Get all preprocessed results files for a dataset.
    
    Reads and returns the contents of files from the preprocessed directory:
    - `preprocess_summary.json` - Preprocessing execution summary
    - `nnUNetPlans.json` - nnU-Net planning configuration
    - `dataset_fingerprint.json` - Dataset fingerprint information
    - `preprocess.log` - Preprocessing log file
    
    If any file is not found, that field will be omitted from the response.
    
    Args:
        BASE_URL: Base URL of the API server
        dataset_id: The full dataset identifier (e.g., "Dataset984_Test")
        timeout_seconds: Request timeout in seconds (default: 10)
    
    Returns:
        Response JSON containing all available files' contents
    
    Raises:
        ServerError: If the request fails
        requests.exceptions.RequestException: For network errors
    """
    url = f"{BASE_URL}/plan_and_preprocess/results/details"
    print(f'Getting all preprocessed results details for dataset: {dataset_id}')
    
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }
    
    params = {
        "dataset_id": dataset_id
    }
    
    try:
        response = requests.get(url,
                               params=params,
                               headers=headers,
                               timeout=timeout_seconds)
        
        if response.status_code == 200:
            response_data = response.json()
            print("Preprocessed results details:", response_data)
            return response_data
        else:
            error_message = f"Failed to get preprocessed results details: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting preprocessed results details: {e}")
        raise

def post_train_run(BASE_URL, dataset_id, timeout_seconds=10):
    """
    Submit a nnU-Net training job.
    
    Enqueues a training job for the specified dataset. The dataset_id must follow
    the pattern 'DatasetXYZ_Name' where XYZ is a 3-digit number.
    
    Training jobs cannot be started while there are prediction jobs in the queue.
    
    Args:
        BASE_URL: Base URL of the API server
        dataset_id: The full dataset identifier (e.g., "Dataset015_CBCTBladder")
        timeout_seconds: Request timeout in seconds (default: 10)
    
    Returns:
        Response JSON containing job_id, dataset_id, and number_of_jobs_ahead
    
    Raises:
        ServerError: If the request fails
        requests.exceptions.RequestException: For network errors
    """
    url = f"{BASE_URL}/train/run"
    print(f'Submitting training job for dataset: {dataset_id}')
    
    # The header must follow the format: Authorization: Bearer <TOKEN>
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }
    
    # Form data for application/x-www-form-urlencoded
    data = {
        "dataset_id": dataset_id
    }
    
    try:
        response = requests.post(url, 
                                data=data,
                                headers=headers,
                                timeout=timeout_seconds)
        
        if response.status_code == 200:
            response_data = response.json()
            print("Success:", response_data)
            return response_data
        else:
            error_message = f"Failed to submit training job: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while submitting training job: {e}")
        raise

def get_train_job_status(BASE_URL, job_id, timeout_seconds=10):
    """
    Check the RQ job status and progress for training jobs.
    
    Args:
        BASE_URL: Base URL of the API server
        job_id: The RQ job ID returned from the `/run` endpoint
        timeout_seconds: Request timeout in seconds (default: 10)
    
    Returns:
        Response JSON containing job status, progress, queue position, and result/error if available
    
    Raises:
        ServerError: If the request fails
        requests.exceptions.RequestException: For network errors
    """
    url = f"{BASE_URL}/train/job_status/{job_id}"
    print(f'Checking training job status for job_id: {job_id}')
    
    # The header must follow the format: Authorization: Bearer <TOKEN>
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }
    
    try:
        response = requests.get(url,
                               headers=headers,
                               timeout=timeout_seconds)
        
        if response.status_code == 200:
            response_data = response.json()
            print("Job status:", response_data)
            return response_data
        else:
            error_message = f"Failed to get training job status: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while checking training job status: {e}")
        raise

def get_training_log_files(BASE_URL, dataset_id, model_folder_name, timeout_seconds=10):
    """
    Get list of training log files for a dataset.
    
    Searches for training log files matching the pattern `fold{n}/training_log_*.txt`
    in the model folder within the dataset's results directory, where `fold{n}` is like `fold0`, `fold1`, etc.
    
    The folder structure is: `{model_folder_name}/fold{n}/training_log_*.txt`
    
    Args:
        BASE_URL: Base URL of the API server
        dataset_id: The full dataset identifier (e.g., "Dataset015_CBCTBladder")
        model_folder_name: The model folder name (e.g., "nnUNetTrainer__nnUNetPlans__3d_fullres")
        timeout_seconds: Request timeout in seconds (default: 10)
    
    Returns:
        Response JSON containing a list of file paths relative to the model folder
    
    Raises:
        ServerError: If the request fails
        requests.exceptions.RequestException: For network errors
    """
    url = f"{BASE_URL}/train/results/training_log_files"
    print(f'Getting training log files list for dataset: {dataset_id}, model folder: {model_folder_name}')
    
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }
    
    params = {
        "dataset_id": dataset_id,
        "model_folder_name": model_folder_name
    }
    
    try:
        response = requests.get(url,
                               params=params,
                               headers=headers,
                               timeout=timeout_seconds)
        
        if response.status_code == 200:
            response_data = response.json()
            print("Training log files:", response_data)
            return response_data
        else:
            error_message = f"Failed to get training log files: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting training log files: {e}")
        raise

def get_training_file_content(BASE_URL, dataset_id, model_folder_name, file_name, timeout_seconds=10):
    """
    Get the content of a specific training log file for a dataset.
    
    Reads and returns the content of a training log file. The file_name should be
    a relative path from the model folder, matching the pattern `fold{n}/training_log_*.txt`.
    
    The folder structure is: `{model_folder_name}/fold{n}/training_log_*.txt`
    
    Args:
        BASE_URL: Base URL of the API server
        dataset_id: The full dataset identifier (e.g., "Dataset015_CBCTBladder")
        model_folder_name: The model folder name (e.g., "nnUNetTrainer__nnUNetPlans__3d_fullres")
        file_name: The relative path to the training log file from the model folder (e.g., "fold0/training_log_2025-01-01_12-00-00.txt")
        timeout_seconds: Request timeout in seconds (default: 10)
    
    Returns:
        Response JSON containing the file content as a text string
    
    Raises:
        ServerError: If the request fails
        requests.exceptions.RequestException: For network errors
    """
    url = f"{BASE_URL}/train/results/log_file_content"
    print(f'Getting training file content for dataset: {dataset_id}, model folder: {model_folder_name}, file: {file_name}')
    
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }
    
    params = {
        "dataset_id": dataset_id,
        "model_folder_name": model_folder_name,
        "file_name": file_name
    }
    
    try:
        response = requests.get(url,
                               params=params,
                               headers=headers,
                               timeout=timeout_seconds)
        
        if response.status_code == 200:
            response_data = response.json()
            print("Training file content retrieved")
            return response_data
        else:
            error_message = f"Failed to get training file content: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting training file content: {e}")
        raise

def get_training_model_folder_names(BASE_URL, dataset_id, timeout_seconds=10):
    """
    Get list of model folder names for a dataset.
    
    Searches for folders in the dataset's results directory that match the pattern
    `*__*__*` (containing exactly two double underscores).
    
    These folders typically represent nnU-Net model configurations, such as:
    - `nnUNetTrainer__nnUNetPlans__3d_fullres`
    - `nnUNetTrainer__nnUNetPlans__2d`
    - `nnUNetTrainer__nnUNetPlans__3d_lowres`
    
    Args:
        BASE_URL: Base URL of the API server
        dataset_id: The full dataset identifier (e.g., "Dataset015_CBCTBladder")
        timeout_seconds: Request timeout in seconds (default: 10)
    
    Returns:
        Response JSON containing a list of folder names matching the pattern
    
    Raises:
        ServerError: If the request fails
        requests.exceptions.RequestException: For network errors
    """
    url = f"{BASE_URL}/train/results/model_folders"
    print(f'Getting model folders list for dataset: {dataset_id}')
    
    headers = {
        "Authorization": f"Bearer {test_user['token']}"
    }
    
    params = {
        "dataset_id": dataset_id
    }
    
    try:
        response = requests.get(url,
                               params=params,
                               headers=headers,
                               timeout=timeout_seconds)
        
        if response.status_code == 200:
            response_data = response.json()
            print("Model folders:", response_data)
            return response_data
        else:
            error_message = f"Failed to get model folders: {response.status_code}, {response.text}"
            print(error_message)
            raise ServerError(error_message)
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while getting model folders: {e}")
        raise