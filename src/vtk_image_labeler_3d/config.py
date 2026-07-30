import os


#################
# ENV load .env file
from dotenv import load_dotenv
load_dotenv()

def get_config():

    # log_dir
    log_dir = os.getenv('log_dir')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # temp_dir
    temp_dir = os.getenv('temp_dir')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir, exist_ok=True)

    keycloak_url = os.getenv('keycloak_url', 'https://login.apps.myphysics.net')
    keycloak_realm = os.getenv('keycloak_realm', 'myphysics')
    # Optional full override; otherwise built from keycloak_url/realm.
    keycloak_registration_url = os.getenv('keycloak_registration_url', '').strip()

    ret = {
        'log_dir': log_dir,
        'temp_dir': temp_dir,
        'nnunet_server_url': os.getenv('nnunet_server_url'),
        'keycloak_url': keycloak_url,
        'keycloak_realm': keycloak_realm,
        'keycloak_registration_url': keycloak_registration_url,
    }

    print('get_config().return=', ret)

    return ret
