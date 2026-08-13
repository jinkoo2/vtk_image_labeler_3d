import requests, os, re, json

class ServerError(Exception):
    """Custom exception for server errors."""
    pass

# Mutable auth session filled by login() after Keycloak authentication.
# Kept as `test_user` name for compatibility with existing Bearer header sites.
# password/base_url are kept in-memory only (not persisted) so the client can
# silently renew an expired access token during a long labeling session.
test_user = {
    "email": None,
    "password": None,
    "base_url": None,
    "token": None,
    "token_exp": None,
    "is_admin": False,
    "roles": [],
}

NNUNET_TRAIN_ROLE = "nnunet-train"
NNUNET_ADMIN_ROLE = "nnunet-admin"

# Renew this many seconds before JWT exp to avoid mid-request expiry races.
_TOKEN_REFRESH_SKEW_SECONDS = 60


def _decode_jwt_payload(access_token):
    """Decode JWT payload without verifying signature (roles / exp only)."""
    import base64

    try:
        parts = (access_token or "").split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        raw = base64.urlsafe_b64decode(payload + padding)
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _roles_from_token(access_token):
    claims = _decode_jwt_payload(access_token)
    roles = claims.get("realm_access", {}).get("roles", []) or []
    return [str(r) for r in roles]


def _exp_from_token(access_token):
    claims = _decode_jwt_payload(access_token)
    exp = claims.get("exp")
    try:
        return int(exp) if exp is not None else None
    except (TypeError, ValueError):
        return None


def set_auth_session(
    access_token,
    user_email=None,
    is_admin=False,
    roles=None,
    password=None,
    base_url=None,
):
    """Store Bearer token (and optional renew credentials) for subsequent API calls."""
    token_roles = list(roles) if roles is not None else _roles_from_token(access_token)
    # Prefer explicit is_admin from login API; also derive from roles if needed.
    is_admin_flag = bool(is_admin) or (NNUNET_ADMIN_ROLE in token_roles)

    test_user["token"] = access_token
    test_user["token_exp"] = _exp_from_token(access_token)
    test_user["email"] = user_email
    test_user["is_admin"] = is_admin_flag
    test_user["roles"] = token_roles
    if password is not None:
        test_user["password"] = password
    if base_url is not None:
        test_user["base_url"] = (base_url or "").rstrip("/") or None


def clear_auth_session():
    test_user["token"] = None
    test_user["token_exp"] = None
    test_user["email"] = None
    test_user["password"] = None
    test_user["base_url"] = None
    test_user["is_admin"] = False
    test_user["roles"] = []


def get_auth_session():
    # Never expose password to callers that dump session for UI/logs.
    session = dict(test_user)
    session.pop("password", None)
    return session


def is_authenticated():
    return bool(test_user.get("token"))


def has_role(role_name):
    """True if the signed-in user has the given Keycloak realm role."""
    if not role_name:
        return False
    roles = test_user.get("roles") or []
    return role_name in roles


def has_nnunet_train_role():
    """True when user can access train/preprocess/predictions dashboard tabs."""
    return has_role(NNUNET_TRAIN_ROLE)


def _token_needs_renewal(skew_seconds=_TOKEN_REFRESH_SKEW_SECONDS):
    """True when there is no token or JWT exp is missing / near / past."""
    token = test_user.get("token")
    if not token:
        return True
    exp = test_user.get("token_exp")
    if exp is None:
        exp = _exp_from_token(token)
        test_user["token_exp"] = exp
    if exp is None:
        # Cannot tell; leave token alone until server returns 401.
        return False
    import time

    return int(time.time()) >= (int(exp) - int(skew_seconds))


def can_renew_auth():
    return bool(
        test_user.get("email")
        and test_user.get("password")
        and test_user.get("base_url")
    )


def renew_auth_session(timeout_seconds=30, force=False):
    """
    Silently re-login with in-memory credentials when the access token is expired
    (or about to expire). Returns True if a renewal was performed.
    """
    if not force and not _token_needs_renewal():
        return False
    if not can_renew_auth():
        raise ServerError(
            "Session token expired. Connect again and sign in to renew."
        )
    email = test_user["email"]
    password = test_user["password"]
    base_url = test_user["base_url"]
    print(f"Renewing access token for {email} at {base_url}")
    login(base_url, email, password, timeout_seconds=timeout_seconds)
    return True


def ensure_auth(skew_seconds=_TOKEN_REFRESH_SKEW_SECONDS):
    """Renew the access token if missing/expired before an API call."""
    if not test_user.get("token"):
        if can_renew_auth():
            renew_auth_session(force=True)
        else:
            raise ServerError("Not logged in. Connect to the server and sign in first.")
        return
    if _token_needs_renewal(skew_seconds=skew_seconds):
        renew_auth_session(force=True)


def _auth_headers():
    ensure_auth()
    token = test_user.get("token")
    if not token:
        raise ServerError("Not logged in. Connect to the server and sign in first.")
    return {"Authorization": f"Bearer {token}"}


def _is_token_expired_response(response):
    """True when the server rejected the request because the JWT expired."""
    if response is None:
        return False
    if response.status_code not in (401, 403):
        return False
    text = (response.text or "").lower()
    if "token expired" in text or "expired signature" in text:
        return True
    try:
        detail = response.json().get("detail")
        detail_s = str(detail).lower() if detail is not None else ""
        if "token expired" in detail_s or "expired" in detail_s:
            return True
    except Exception:
        pass
    # Generic unauthorized often means expired Keycloak JWT after a long session.
    return response.status_code == 401


def request_with_auth(method, url, timeout=30, retry_auth=True, **kwargs):
    """
    Authenticated requests.* wrapper: renews JWT when near expiry, and retries
    once after a silent re-login if the server reports token expired / 401.
    """
    headers = dict(kwargs.pop("headers", None) or {})
    headers.update(_auth_headers())
    kwargs["headers"] = headers
    kwargs.setdefault("timeout", timeout)

    response = requests.request(method, url, **kwargs)
    if retry_auth and _is_token_expired_response(response) and can_renew_auth():
        print("Server reported expired token; renewing and retrying once...")
        renew_auth_session(force=True)
        headers = dict(kwargs.get("headers") or {})
        headers.update(_auth_headers())
        kwargs["headers"] = headers
        # File uploads: reopen / rewind if caller passed an open file that was read.
        files = kwargs.get("files")
        if files:
            for _key, value in list(files.items() if isinstance(files, dict) else []):
                file_obj = value[1] if isinstance(value, tuple) and len(value) >= 2 else value
                if hasattr(file_obj, "seek"):
                    try:
                        file_obj.seek(0)
                    except Exception:
                        pass
        response = requests.request(method, url, **kwargs)
    return response


def login(BASE_URL, email, password, timeout_seconds=30):
    """
    POST /auth/login - authenticate against Keycloak via the nnU-Net server.

    Returns dict with access_token, token_type, user_email, is_admin and
    stores the token (plus in-memory credentials for auto-renewal) for
    subsequent API calls.
    """
    base = (BASE_URL or "").rstrip("/")
    url = f"{base}/auth/login"
    print(f"Logging in at {url} as {email}")
    try:
        response = requests.post(
            url,
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=timeout_seconds,
        )
    except requests.exceptions.RequestException as e:
        raise ServerError(f"Login request failed: {e}") from e

    if response.status_code != 200:
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except Exception:
            pass
        raise ServerError(f"Login failed ({response.status_code}): {detail}")

    data = response.json()
    token = data.get("access_token")
    if not token:
        raise ServerError(f"Login response missing access_token: {data}")

    set_auth_session(
        access_token=token,
        user_email=data.get("user_email") or email,
        is_admin=bool(data.get("is_admin", False)),
        password=password,
        base_url=base,
    )
    print(
        f"Logged in as {test_user['email']} "
        f"(admin={test_user['is_admin']}, roles={test_user.get('roles')}, "
        f"exp={test_user.get('token_exp')})"
    )
    return data


def _filename_from_content_disposition(response, fallback):
    content_disposition = response.headers.get("Content-Disposition", "")
    match = re.search(r'filename="([^"]+)"', content_disposition, flags=re.IGNORECASE)
    if not match:
        match = re.search(r'filename=([^;]+)', content_disposition, flags=re.IGNORECASE)
    if match:
        return os.path.basename(match.group(1).strip().strip('"'))
    return fallback


def _raise_for_status(response, action):
    if response.status_code == 200:
        return
    detail = response.text
    try:
        detail = response.json().get("detail", detail)
    except Exception:
        pass
    if _is_token_expired_response(response):
        error_message = (
            "Failed %s: session token expired and could not be renewed. "
            "Connect again and sign in. (%s: %s)"
            % (action, response.status_code, detail)
        )
    else:
        error_message = "Failed %s: %s, %s" % (action, response.status_code, detail)
    print(error_message)
    raise ServerError(error_message)


def get_ping(BASE_URL, timeout_seconds=10):
    """
    Ping the server and return the response with timeout handling.
    """
    url = f"{BASE_URL}/status/ping"
    print(f'Pinging the server at {url}')
    
    # The header must follow the format: Authorization: Bearer <TOKEN>
    headers = _auth_headers()

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
    headers = _auth_headers()

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
    headers = _auth_headers()

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
    headers = _auth_headers()

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
        

def get_image_meta(BASE_URL, dataset_id, images_for, num, timeout_seconds=10):
    """
    Fetch optional image-set metadata for a case.
    Never 404s for a missing meta file; response includes exists/meta/error.
    """
    headers = _auth_headers()
    params = {
        "dataset_id": dataset_id,
        "images_for": images_for,
        "num": num,
    }
    try:
        response = requests.get(
            f"{BASE_URL}/datasets/get_image_meta",
            params=params,
            headers=headers,
            timeout=timeout_seconds,
        )
        _raise_for_status(response, "fetching image meta")
        return response.json()
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching image meta: {e}")
        raise


def get_label_meta(BASE_URL, dataset_id, images_for, num, timeout_seconds=10):
    """
    Fetch optional label metadata for a case (status, modified_by, etc.).
    Never 404s for a missing meta file; response includes exists/meta/error.
    """
    headers = _auth_headers()
    params = {
        "dataset_id": dataset_id,
        "images_for": images_for,
        "num": num,
    }
    try:
        response = requests.get(
            f"{BASE_URL}/datasets/get_label_meta",
            params=params,
            headers=headers,
            timeout=timeout_seconds,
        )
        _raise_for_status(response, "fetching label meta")
        return response.json()
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching label meta: {e}")
        raise


def update_image_meta(BASE_URL, dataset_id, images_for, num, meta, timeout_seconds=10):
    """
    Create or replace image-set metadata for a case.
    Full-replace semantics: send the complete merged meta object.
    """
    params = {
        "dataset_id": dataset_id,
        "images_for": images_for,
        "num": num,
    }
    try:
        response = request_with_auth(
            "PUT",
            f"{BASE_URL}/datasets/update_image_meta",
            params=params,
            json=meta,
            timeout=timeout_seconds,
        )
        _raise_for_status(response, "updating image meta")
        return response.json()
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while updating image meta: {e}")
        raise


def update_label_meta(BASE_URL, dataset_id, images_for, num, meta, timeout_seconds=10):
    """
    Create or replace label metadata for a case (status, modified_by, label_stats, ...).
    """
    params = {
        "dataset_id": dataset_id,
        "images_for": images_for,
        "num": num,
    }
    try:
        response = request_with_auth(
            "PUT",
            f"{BASE_URL}/datasets/update_label_meta",
            params=params,
            json=meta,
            timeout=timeout_seconds,
        )
        _raise_for_status(response, "updating label meta")
        return response.json()
    except requests.exceptions.Timeout:
        print(f"Request timed out after {timeout_seconds} seconds.")
        raise
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while updating label meta: {e}")
        raise


def download_dataset_image(BASE_URL, dataset_id, images_for, num, out_dir, ch_number=0):
    """Download one channel image using the v3 download_image endpoint."""
    headers = _auth_headers()

    if not os.path.exists(out_dir):
        print(f"Creating out_dir: {out_dir}")
        os.makedirs(out_dir)

    image_params = {
        "dataset_id": dataset_id,
        "images_for": images_for,
        "num": num,
        "ch_number": ch_number,
    }
    image_response = requests.get(
        f"{BASE_URL}/datasets/download_image",
        params=image_params,
        headers=headers,
    )
    _raise_for_status(image_response, "downloading base image")

    base_image_filename = _filename_from_content_disposition(
        image_response, f"image_{num}_{ch_number:04d}.mha"
    )
    base_image_path = os.path.join(out_dir, base_image_filename)
    print(f"Saving base image to: {base_image_path}")
    with open(base_image_path, "wb") as f:
        f.write(image_response.content)

    return {
        "base_image_filename": base_image_filename,
        "base_image_url": (
            f"/datasets/download_image?dataset_id={dataset_id}"
            f"&images_for={images_for}&num={num}&ch_number={ch_number}"
        ),
        "downloaded_base_image_path": base_image_path,
    }


def download_dataset_label(BASE_URL, dataset_id, images_for, num, out_dir):
    """Download a case label using the v3 download_label endpoint."""
    headers = _auth_headers()

    if not os.path.exists(out_dir):
        print(f"Creating out_dir: {out_dir}")
        os.makedirs(out_dir)

    label_params = {
        "dataset_id": dataset_id,
        "images_for": images_for,
        "num": num,
    }
    label_response = requests.get(
        f"{BASE_URL}/datasets/download_label",
        params=label_params,
        headers=headers,
    )
    if label_response.status_code == 404:
        raise ServerError(
            f"Label file not found for dataset_id={dataset_id}, "
            f"images_for={images_for}, num={num}"
        )
    _raise_for_status(label_response, "downloading label image")

    labels_filename = _filename_from_content_disposition(
        label_response, f"image_{num}.mha"
    )
    label_image_path = os.path.join(out_dir, labels_filename)
    print(f"Saving label image to: {label_image_path}")
    with open(label_image_path, "wb") as f:
        f.write(label_response.content)

    return {
        "labels_filename": labels_filename,
        "labels_url": (
            f"/datasets/download_label?dataset_id={dataset_id}"
            f"&images_for={images_for}&num={num}"
        ),
        "downloaded_labels_image_path": label_image_path,
    }


def download_dataset_images_and_labels(BASE_URL, dataset_id, images_for, num, out_dir, ch_number=0):
    """
    Download one channel image and its label using the v3 download endpoints.
    """
    image_result = download_dataset_image(
        BASE_URL, dataset_id, images_for, num, out_dir, ch_number=ch_number
    )

    labels_filename = None
    label_image_path = None
    try:
        label_result = download_dataset_label(
            BASE_URL, dataset_id, images_for, num, out_dir
        )
        labels_filename = label_result["labels_filename"]
        label_image_path = label_result["downloaded_labels_image_path"]
    except ServerError as e:
        if "Label file not found" in str(e):
            print(
                f"Label file not found for dataset_id={dataset_id}, "
                f"images_for={images_for}, num={num}. Continuing without labels."
            )
        else:
            raise

    result = {
        "base_image_filename": image_result["base_image_filename"],
        "labels_filename": labels_filename,
        "base_image_url": image_result["base_image_url"],
        "labels_url": (
            f"/datasets/download_label?dataset_id={dataset_id}"
            f"&images_for={images_for}&num={num}"
        ),
    }
    print("Image filename:", result["base_image_filename"])
    print("Label filename:", result["labels_filename"])

    return {
        "image_and_labels": result,
        "downloaded_base_image_path": image_result["downloaded_base_image_path"],
        "downloaded_labels_image_path": label_image_path,
    }


def post_dataset_json(BASE_URL, data):
    """
    post a dataset
    """
    response = request_with_auth(
        "POST",
        f"{BASE_URL}/datasets/new",
        json=data,
        headers={"Content-Type": "application/json"},
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to add a dataset: {response.status_code}, {response.text}")
        return None

def post_image_and_labels(BASE_URL, dataset_id, images_for, image_path, labels_path, ch_number=0):
    """
    v3 workflow: reserve a case with add_image_set, then upload channel image and label.
    Returns the updated dataset_json counters for compatibility with existing callers.
    """
    headers = _auth_headers()

    try:
        set_response = requests.post(
            f"{BASE_URL}/datasets/add_image_set",
            headers=headers,
            data={
                "dataset_id": dataset_id,
                "images_for": images_for,
            },
        )
        _raise_for_status(set_response, "reserving image set")
        set_data = set_response.json()
        num = set_data["num"]
        dataset_json = set_data["dataset_json"]
        print(f"Reserved image set num={num}")

        with open(image_path, "rb") as img_file:
            image_response = requests.post(
                f"{BASE_URL}/datasets/add_image",
                headers=headers,
                data={
                    "dataset_id": dataset_id,
                    "images_for": images_for,
                    "num": num,
                    "ch_number": ch_number,
                },
                files={"image": img_file},
            )
        _raise_for_status(image_response, "posting image")
        print("Success:", image_response.json())

        with open(labels_path, "rb") as lbl_file:
            label_response = requests.post(
                f"{BASE_URL}/datasets/add_label",
                headers=headers,
                data={
                    "dataset_id": dataset_id,
                    "images_for": images_for,
                    "num": num,
                },
                files={"label": lbl_file},
            )
        _raise_for_status(label_response, "posting label")
        print("Success:", label_response.json())

        return {"num": num, "dataset_json": dataset_json}
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while pushing images to the server: {e}")
        raise


def update_image_and_labels(BASE_URL, dataset_id, images_for, num, image_path, labels_path, ch_number=0):
    """
    v3 workflow: upsert one channel image and the label for an existing case.

    Uses PUT update_* when the file already exists. If the server returns 404
    (common when an image was opened with no label yet), falls back to POST add_*.
    Access tokens are auto-renewed when expired (silent re-login).
    """
    try:
        image_data = {
            "dataset_id": dataset_id,
            "images_for": images_for,
            "num": num,
            "ch_number": ch_number,
        }
        with open(image_path, "rb") as img_file:
            image_response = request_with_auth(
                "PUT",
                f"{BASE_URL}/datasets/update_image",
                data=image_data,
                files={"image": img_file},
            )
            if image_response.status_code == 404:
                print(
                    f"No existing image for num={num}, ch_number={ch_number}. "
                    "Falling back to POST /add_image."
                )
                img_file.seek(0)
                image_response = request_with_auth(
                    "POST",
                    f"{BASE_URL}/datasets/add_image",
                    data=image_data,
                    files={"image": img_file},
                )
        _raise_for_status(image_response, "updating image")
        image_result = image_response.json()
        print("Success:", image_result)

        label_data = {
            "dataset_id": dataset_id,
            "images_for": images_for,
            "num": num,
        }
        with open(labels_path, "rb") as lbl_file:
            label_response = request_with_auth(
                "PUT",
                f"{BASE_URL}/datasets/update_label",
                data=label_data,
                files={"label": lbl_file},
            )
            if label_response.status_code == 404:
                print(
                    f"No existing label for num={num}. "
                    "Falling back to POST /add_label."
                )
                lbl_file.seek(0)
                label_response = request_with_auth(
                    "POST",
                    f"{BASE_URL}/datasets/add_label",
                    data=label_data,
                    files={"label": lbl_file},
                )
        _raise_for_status(label_response, "updating label")
        label_result = label_response.json()
        print("Success:", label_result)

        return {
            "image": image_result,
            "label": label_result,
            "message": "Image and label updated successfully.",
        }
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while pushing images to the server: {e}")
        raise


def delete_image_and_labels(BASE_URL, dataset_id, images_for, num):
    """
    v3 workflow: delete an entire case (all channels + label) via delete_image_set.
    """
    headers = _auth_headers()

    try:
        params = {
            "dataset_id": dataset_id,
            "images_for": images_for,
            "num": num,
        }
        response = requests.delete(
            f"{BASE_URL}/datasets/delete_image_set",
            headers=headers,
            params=params,
        )
        _raise_for_status(response, "deleting image and label pair")
        response_data = response.json()
        print("Success:", response_data)
        return response_data
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while pushing images to the server: {e}")
        raise



def renumber_image_sets(BASE_URL, dataset_id, images_for):
    """
    v3: renumber train or test cases to contiguous 0..N-1 via POST /datasets/renumber_image_sets.
    """
    headers = _auth_headers()

    try:
        params = {
            "dataset_id": dataset_id,
            "images_for": images_for,
        }
        response = requests.post(
            f"{BASE_URL}/datasets/renumber_image_sets",
            headers=headers,
            params=params,
        )
        _raise_for_status(response, "renumbering image sets")
        response_data = response.json()
        print("Success:", response_data)
        return response_data
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while renumbering image sets: {e}")
        raise


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

        response = requests.post(url, data=form_data, files=files, headers=_auth_headers()   )

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

        response = requests.post(url, data=form_data, files=files, headers=_auth_headers())

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
                                headers=_auth_headers())

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
                                 headers=_auth_headers())

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


def get_approved_models(BASE_URL, timeout_seconds=30):
    """GET /models/list/approved — list models marked approved for inference."""
    url = f"{BASE_URL}/models/list/approved"
    print(f"Fetching approved models: {url}")
    try:
        response = requests.get(url, headers=_auth_headers(), timeout=timeout_seconds)
        _raise_for_status(response, "fetching approved models")
        data = response.json()
        print(f"Approved models: {data}")
        return data if isinstance(data, list) else []
    except ServerError:
        raise
    except Exception as e:
        print(f"An error occurred while fetching approved models: {e}")
        raise


def get_model_detail(BASE_URL, dataset_id, trainer, plans, configuration, timeout_seconds=30):
    """GET /models/model_detail — plans.json + dataset.json for a trained model."""
    url = f"{BASE_URL}/models/model_detail"
    params = {
        "dataset_id": dataset_id,
        "trainer": trainer,
        "plans": plans,
        "configuration": configuration,
    }
    print(f"Fetching model detail: {url} params={params}")
    try:
        response = requests.get(url, params=params, headers=_auth_headers(), timeout=timeout_seconds)
        _raise_for_status(response, "fetching model detail")
        data = response.json()
        print(f"Model detail keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        return data
    except ServerError:
        raise
    except Exception as e:
        print(f"An error occurred while fetching model detail: {e}")
        raise


def post_prediction(
    BASE_URL,
    model_dataset_id,
    image_id,
    channel_image_paths,
    trainer="nnUNetTrainer",
    plans="nnUNetPlans",
    configuration="3d_lowres",
    timeout_seconds=120,
):
    """
    POST /predictions/predict

    channel_image_paths: ordered list of local file paths (channel 0, 1, ...).
    Channel 0 is sent as form field `image` (current API). Additional channels are
    also attached as `channel_{i}` for forward compatibility with multi-channel servers.
    """
    if not channel_image_paths:
        raise ValueError("At least one channel image path is required.")

    url = f"{BASE_URL}/predictions/predict"
    form_data = {
        "dataset_id": model_dataset_id,
        "image_id": image_id,
        "trainer": trainer,
        "plans": plans,
        "configuration": configuration,
        "num_channels": str(len(channel_image_paths)),
    }

    opened = []
    try:
        files = []
        for i, path in enumerate(channel_image_paths):
            basename = os.path.basename(path)
            if i == 0:
                fh_image = open(path, "rb")
                opened.append(fh_image)
                files.append(("image", (basename, fh_image, "application/octet-stream")))
            fh = open(path, "rb")
            opened.append(fh)
            files.append((f"channel_{i}", (basename, fh, "application/octet-stream")))

        print(f"Posting prediction to {url} dataset_id={model_dataset_id} channels={len(channel_image_paths)}")
        response = requests.post(
            url,
            data=form_data,
            files=files,
            headers=_auth_headers(),
            timeout=timeout_seconds,
        )
        _raise_for_status(response, "posting prediction")
        data = response.json()
        print(f"Prediction submit response: {data}")
        return data
    except ServerError:
        raise
    except Exception as e:
        print(f"An error occurred while posting prediction: {e}")
        raise
    finally:
        for fh in opened:
            try:
                fh.close()
            except Exception:
                pass


def get_prediction_job_status(BASE_URL, job_id, timeout_seconds=30):
    """GET /predictions/status/{job_id}"""
    url = f"{BASE_URL}/predictions/status/{job_id}"
    try:
        response = requests.get(url, headers=_auth_headers(), timeout=timeout_seconds)
        _raise_for_status(response, "fetching prediction job status")
        return response.json()
    except ServerError:
        raise
    except Exception as e:
        print(f"An error occurred while fetching prediction job status: {e}")
        raise


def delete_prediction(BASE_URL, dataset_id, req_id):
    url = f"{BASE_URL}/predictions/delete"
    params = {"dataset_id": dataset_id, "req_id": req_id}
    print(f"nnunet_service.delete_prediction: url={url}, params={params}")
    
    try:
        response = requests.delete(url, 
                                params=params,
                                headers=_auth_headers())

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
    meta_response = requests.get(meta_url, params=meta_params, headers=_auth_headers())

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
                                headers=_auth_headers())
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
    headers = _auth_headers()
    
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
    headers = _auth_headers()
    
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
    
    headers = _auth_headers()
    
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
    
    headers = _auth_headers()
    
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
    
    headers = _auth_headers()
    
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
    
    headers = _auth_headers()
    
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
    headers = _auth_headers()
    
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
    headers = _auth_headers()
    
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
    
    headers = _auth_headers()
    
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
    
    headers = _auth_headers()
    
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
    
    headers = _auth_headers()
    
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