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
