import requests
from config import Config
from disk_publish import DiskPublish

def get_access_token(vbr_server, username, password):
    url = f'{vbr_server}/api/oauth2/token'
    headers = {'x-api-version': '1.2-rev0'}
    payload = {
        'grant_type': 'password',
        'username': username,
        'password': password
    }
    response = requests.post(url, headers=headers, data=payload, verify=False)
    response.raise_for_status()
    return response.json()['access_token']

def log_out(vbr_server, token):
    url = f'{vbr_server}/api/oauth2/logout'
    headers = {'x-api-version': '1.2-rev0', 'Authorization': f'Bearer {token}'}
    response = requests.post(url, headers=headers, verify=False)
    response.raise_for_status()

if __name__ == '__main__':
    config = Config('config.json')
    config_data = config.get_config()

    token = get_access_token(config_data['vbr_server'], config_data['username'], config_data['password'])

    dp01 = DiskPublish(config_data['vbr_server'], config_data['target_server'], config_data['VM_name'], token, config_data['number_of_rp'], config_data['credential_description'])
    results = dp01.get_credential_id()
    print(results)

    log_out(config_data['vbr_server'], token)

