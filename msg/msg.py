import json
from auth.auth import base_url, session

### START CONFIG ###
sample_msg_id = '' # for testing
### END CONFIG ###

def get_message(message_id=sample_msg_id):
    """
    gets a msg by id
    """
    url = base_url + "messages/" + "'" + message_id + "'"
    request = session.get(url)
    return json.loads(request.content)
    

def get_messages(categories=None):
    """
    get all messages, 
    or optionally by category
    """
    if categories:
        return get_messages_by_category(category)
    else:
        return get_all_messages()


def get_all_messages():
    """
    all the msgs,
    paginated into memory
    """
    url = base_url + 'messages'
    response = session.get(url)
    content = json.loads(response.content)
    messages = []
    while 'value' in content.keys():
        for message in content['value']:
            messages.append(message)
        if '@odata.nextLink' in content.keys():
            response = session.get(content['@odata.nextLink'])
            content = json.loads(response.content)
        else:
            break
    return messages


def get_categories():
    """
    all categories, keyed by {'status':[],'file'[]}
    i.e., there are category labels for 
    each foia file and each status
    """
    url = base_url + 'outlook/masterCategories'
    response = session.get(url)
    content = json.loads(response.content)
    categories = {'status':[],'file':[]}
    while 'value' in  content.keys():
        for cat in content['value']:
            cat_name = cat['displayName']
            if 'status' in cat_name:
                categories['status'].append(cat_name)
            elif 'file' in cat_name:
                categories['file'].append(cat_name)
            else:
                # not expected
                print('misc category: ',cat_name)
        if '@odata.nextLink' in content.keys():
            response = session.get(content['@odata.nextLink'])
            content = json.loads(response.content)
        else:
            break
    return categories


def get_conversation(conversation_id):
    """
    convesations = threads
    returns all messages in a thread
    """
    url = base_url + "messages?filter=conversationId eq '" + conversation_id + "'"
    response = session.get(url)
    content = json.loads(response.content)
    messages = []
    while 'value' in content.keys():
        for message in content['value']:
            messages.append(message)
        if '@odata.nextLink' in content.keys():
            response = session.get(content['@odata.nextLink'])
            content = json.loads(response.content)
        else:
            break
    return messages


def get_msg_fileslug(msg):
    """
    for a given message,
    which file/foia is this?
    checks entire message thread for category labels
    """
    convo = get_conversation(msg['conversationId'])
    for msg in convo:
        for cat in msg['categories']:
            if 'file' in cat:
                return cat