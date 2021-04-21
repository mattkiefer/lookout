import json
import requests.exceptions

from azure.identity import ClientSecretCredential
from msgraphcore import GraphSession

### START CONFIG ###
param_path = 'auth/secrets.json'
config = json.load(open(param_path))
base_url = '/users/' + config['sample_user'] + '/'
### END CONFIG ###


def get_cred():
    # authenticate
    credential = ClientSecretCredential(
        tenant_id = config["tenant_id"],
        client_id = config["client_id"],
        client_secret = config["client_secret"])
    return credential


def get_session():
    # start a session
    graph_session = GraphSession(get_cred(), config["scope"])
    return graph_session

session = get_session()
