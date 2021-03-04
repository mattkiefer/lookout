import json, csv, base64, os
import requests.exceptions
from pathlib import Path
from azure.identity import ClientSecretCredential
from msgraphcore import GraphSession

# config #

param_path = 'secrets.json'
config = json.load(open(param_path))
base_url = '/users/' + config['sample_user'] + '/'
status_report_path = 'status_report.csv'

onedrive_project_folder_name = 'the_unarmed'
onedrive_foia_responses_folder_name = 'foia-responses'
onedrive_foia_responses_path = onedrive_project_folder_name + '/' + onedrive_foia_responses_folder_name
local_download_dir = '/tmp/'

sample_msg_id = 'AAMkADc5ODdiMGQ5LTJmZTktNGJkNC04Mjk3LWVkN2I1ODVkYzk0YwBGAAAAAAASq04FJ7T0TLTsSdv7LFIiBwD5Pih54zEFRZbvRflBxgmJAAAAAAEJAAD5Pih54zEFRZbvRflBxgmJAAA8U2g5AAA='

disallowed_exts = ['jpg','jpeg','png']


# auth #

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


# msgs #

def get_message(message_id=sample_msg_id):
    """
    """
    url = base_url + "messages/" + "'" + message_id + "'"
    request = session.get(url)
    return json.loads(request.content)
    

def get_messages(categories=None):
    """
    loads in memory
    """
    if categories:
        return get_messages_by_category(category)
    else:
        return get_all_messages()


def get_all_messages():
    """
    all the msgs
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
    all categories keyed by 
    {'status':[],'file'[]}
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
    convo = get_conversation(msg['conversationId'])
    for msg in convo:
        for cat in msg['categories']:
            if 'file' in cat:
                return cat


# report #
def get_messages_by_category(cat_name):
    """
    one at a time
    """
    # TODO scan entire thread
    url = base_url + "messages?$filter=categories/any(a:a eq '{category}')".format(category=cat_name)
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
    

def basic_report():
    """
    assumes no response = 'status/sent'
    """
    outfile = open(status_report_path,'w')
    headers = ['file','status']
    outcsv = csv.DictWriter(outfile,headers)
    outcsv.writeheader()

    file_names = get_categories()['file']
    for file_name in file_names:
        # all status labels applied to messages for this foia
        statuses = get_statuses(file_name)
        # derive the the most relevant status
        status = get_status(statuses)
        row = {'file':file_name,'status':status}
        print(row)
        outcsv.writerow(row)
    outfile.close()


def get_statuses(file_slug):
    """
    get messages + their threads
    collect their status tags,
    make other inferences
    """
    messages = get_messages_by_category(file_slug)
    statuses = set()
    for message in messages:
        conversation = get_conversation(message['conversationId'])
        for convo_msg in conversation:
            for cat_name in convo_msg['categories']:
                statuses.add(cat_name)
            # catch flags
            if convo_msg['flag']['flagStatus'] == 'flagged':
                statuses.add('flagged')
            if '@washpost.com' not in convo_msg['sender']['emailAddress']:
                statuses.add('replied')
            # catch attachments
            if convo_msg['hasAttachments']:
                statuses.add('attachment')
    return statuses


def get_status(statuses):
    if 'flagged' in statuses:
        return 'flagged'
    if 'status/appeal' in statuses:
        return 'appeal'
    if 'status/refile' in statuses:
        return 'refile'
    if 'status/shipped' in statuses:
        return 'shipped'
    if 'status/done' in statuses:
        return 'done'
    if 'status/denied' in statuses:
        return 'denied'
    if 'status/partial' in statuses:
        return 'partially complete'
    if 'attachment' in statuses:
        return 'attachment'
    if 'status/replied' in statuses:
        return 'replied'
    # inelegant bail out
    if 'status/portal' in statuses:
        return 'portal'
    if 'status/sent' in statuses:
        return 'sent'
    else:
        return None


def get_correspondence():
    pass

# atts
def sweep():
    """
    move attachments
    from outlook
    to onedrive
    """
    # keep track of what folders exist
    # brittle!
    folders = []
    foia_folder_url = base_url + 'drive/root:/' + onedrive_foia_responses_path
    foia_folder = json.loads(session.get(foia_folder_url).content)
    folder_items_url = base_url + 'drive/items/' + foia_folder['id'] + '/children'
    folder_items = json.loads(session.get(folder_items_url).content)['value']
    for item in folder_items:
        if 'folder' in item.keys():
            folders.append(item['name'].replace('/','-'))

    # get the atts from 'status/done' msgs
    done_msgs = get_messages_by_category('status/done')
    partial_msgs = get_messages_by_category('status/partial')
    msgs = done_msgs + partial_msgs

    for msg in msgs:
        print('msg id:', msg['id'])
        # skip stuff that shipped
        # TODO: consider skipping stuff that exists in OneDrive instead
        if 'status/shipped' not in msg['categories']:
            fileslug = get_msg_fileslug(msg)
            if not fileslug: 
                #TODO figure out these cases
                continue
            folder_name = fileslug.replace('/','-')

            # get atts
            get_atts_url = base_url + 'messages/' + msg['id'] + '/attachments'
            atts_content = json.loads(session.get(get_atts_url).content)
            if atts_content:
                atts = atts_content['value']
            else:
                import ipdb; ipdb.set_trace()
                continue
            att_list = []
            # first build a list of usable attachments
            for att in atts:
                print('att:', att['name'])
                ext = att['name'].split('.')[-1]
                # don't ship useless files
                if ext in disallowed_exts:
                    print('disallowing',att['name'])
                    continue
                # download
                print('allowing',att['name'])
                att_list.append(att)
            # then upload those
            if att_list:
                # create folder if it doesn't exist
                if folder_name not in folders:
                    create_folder_url = base_url + 'drive/items/' + foia_folder['id'] + '/children'
                    body = {"name":folder_name,"folder": { },"@microsoft.graph.conflictBehavior": "fail"}
                    folder = session.post(create_folder_url,headers={'Content-Type':'application/json'},data=json.dumps(body))
                    print('creating',folder_name)
                print('found',folder_name)

            for att in att_list:
                buffer_file_path = local_download_dir + att['name']
                buffer_file = open(buffer_file_path,'wb')
                if 'contentBytes' not in att.keys():
                    continue
                try:
                    buffer_file.write(base64.b64decode(att['contentBytes']))
                except Exception as e:
                    import ipdb; ipdb.set_trace()
                buffer_file.close()
                print('downloaded:',att['name'])
                # where to put stuff
                file_folder_url = foia_folder_url + '/' + folder_name
                file_folder_file_url = file_folder_url + '/' + att['name'] + ':/content' 
                
                # upload
                filePath = Path(buffer_file_path)
                bytez = filePath.read_bytes()
                try:
                    session.put(file_folder_file_url,headers={'Content-Type':'application/pdf'},data=bytez)
                    print('uploading',att['name'])
                except requests.exceptions.HTTPError as err:
                    # TODO: haven't figured out large uploads yet so pass
                    print(err)
                # clean up
                print('removing:',buffer_file_path)
                os.remove(buffer_file_path)            
            

