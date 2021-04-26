import json
import requests.exceptions

from azure.identity import ClientSecretCredential
from msgraphcore import GraphSession

from config.config import secrets

### START CONFIG ###
base_url = '/users/' + secrets['user'] + '/'
### END CONFIG ###


def get_cred():
    # authenticate
    credential = ClientSecretCredential(
        tenant_id = secrets["tenant_id"],
        client_id = secrets["client_id"],
        client_secret = secrets["client_secret"])
    return credential


def get_session():
    # start a session
    graph_session = GraphSession(get_cred(), secrets["scope"])
    return graph_session

session = get_session()
