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

    ret = {
        'log_dir': log_dir,
        'temp_dir': temp_dir,
        'nnunet_server_url': os.getenv('nnunet_server_url')
    }

    print('get_config().return=', ret)

    return ret
