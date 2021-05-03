import json, base64, os, urllib
from pathlib import Path
import requests.exceptions
from auth.auth import base_url, session
from config.config import project_configs
from msg.msg import get_messages_by_category, get_msg_fileslug

### START CONFIG ###
disallowed_exts = ['jpg','jpeg','png']
local_download_dir = project_configs['local_download_dir']
base_project_folder_name = project_configs['base_project_folder_name']
foia_response_folder_name = project_configs['foia_response_folder_name']
foia_response_folder_path = base_project_folder_name + '/' + foia_response_folder_name
### END CONFIG ###

def sweep():
    """
    move attachments
    from outlook
    to onedrive
    """
    # keep track of what folders exist already in foia_response directory
    folders = []
    foia_folder_url = base_url + 'drive/root:/' + foia_response_folder_path
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
                    print(e)
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
                    upload(buffer_file_path, folder_name, att['name'], bytez)
                    print('uploading',att['name'])
                except requests.exceptions.HTTPError as err:
                    # TODO: haven't figured out large uploads yet so pass
                    print(err)
                    import ipdb; ipdb.set_trace()
                # clean up
                print('removing:',buffer_file_path)
                os.remove(buffer_file_path)            
            # TODO: apply status/shipped to mail messages


def upload(file_path, folder_name, file_name, bytez):
    # cribbed https://gist.github.com/keathmilligan/590a981cc629a8ea9b7c3bb64bfcb417
    file_name = urllib.parse.quote(file_name)
    result = session.post(
            f'{base_url}drive/root:/{foia_response_folder_path}/{folder_name}/{file_name}:/createUploadSession', # TODO fix this call
        json={
            '@microsoft.graph.conflictBehavior': 'fail', # dupe filenames won't upload TODO: consider diffing
            'description': file_name,
            'fileSystemInfo': {'@odata.type': 'microsoft.graph.fileSystemInfo'},
            'name': file_name
        }
    )
    result.raise_for_status()
    upload_session = result.json()
    upload_url = upload_session['uploadUrl']

    st = os.stat(file_path)
    size = st.st_size
    CHUNK_SIZE = 10485760
    chunks = int(size / CHUNK_SIZE) + 1 if size % CHUNK_SIZE > 0 else 0
    with open(file_path, 'rb') as fd:
        start = 0
        for chunk_num in range(chunks):
            chunk = fd.read(CHUNK_SIZE)
            bytes_read = len(chunk)
            upload_range = f'bytes {start}-{start + bytes_read - 1}/{size}'
            print(f'chunk: {chunk_num} bytes read: {bytes_read} upload range: {upload_range}')
            result = session.put(
                upload_url,
                headers={
                    'Content-Length': str(bytez),
                    'Content-Range': upload_range
                },
                data=chunk
            )
            result.raise_for_status()
            start += bytes_read
