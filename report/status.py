import csv, json
from auth.auth import base_url, session
from msg.msg import get_conversation, get_messages_by_category 

### START CONFIG ###
configs = json.loads(open('config/project_configs.json').read())
status_report_path = configs['status_report_path']
project_folder_name = configs['project_folder_name']
workbook_id = configs['workbook_id']
worksheet_id = configs['worksheet_id']
table_id = configs['table_id']
sender_domain = configs['sender_domain']
### END CONFIG ###



def get_statuses(file_slug):
    """
    loop through messages tied to a foia,
    return a list of status labels 
    + associated messages
    """
    messages = get_messages_by_category(file_slug)
    statuses = {}
    for message in messages:
        conversation = get_conversation(message['conversationId'])
        for convo_msg in conversation:
            for cat_name in convo_msg['categories']:
                if cat_name not in statuses:
                    statuses[cat_name] = {}
                statuses[cat_name][convo_msg['id']] = convo_msg
            # catch flags
            if convo_msg['flag']['flagStatus'] == 'flagged':
                if 'flagged' not in statuses:
                    statuses['flagged'] = {}
                statuses['flagged'][convo_msg['id']] = convo_msg
            if sender_domain not in convo_msg['sender']['emailAddress']:
                if 'replied' not in statuses:
                    statuses['replied'] = {}
                statuses['replied'][convo_msg['id']] = convo_msg
                #TODO fix bug where senders show up in replies
            # catch attachments
            # TODO: filter out bad att extensions
            if convo_msg['hasAttachments']:
                if 'attachment' not in statuses:
                    statuses['attachment'] = {}
                statuses['attachment'][convo_msg['id']] = convo_msg
    return statuses


def make_msg_link(msg):
    return '=HYPERLINK("' +  msg["webLink"] + '","msg_link")' 


def get_request_status_links(status,statuses):
    """
    return link to most recent msg
    for a given status
    """
    if status in statuses:
        sorted_msgs = sorted([statuses[status][msg] for msg in statuses[status]], key = lambda x: x['sentDateTime'], reverse=True)
        if sorted_msgs:
            return make_msg_link(sorted_msgs[0])
    else:
        return ""


def get_status(statuses):
    """
    derive a summary status
    from the collection of msg statuses
    """
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
    if 'status/portal' in statuses:
        return 'portal'
    if 'status/sent' in statuses:
        return 'sent'
    else:
        return None


def update_report(data=None):
    # TODO fix args and weird handling
    if not data:
        data = get_sharepoint_status_report()
    new_report = []
    for row in data:
        update = get_request_update(slugify(row))
        row['status'] = update['status']
        row['flagged?'] = get_request_status_links('flagged',update['statuses'])
        row['done?'] = get_request_status_links('status/done', update['statuses'])
        row['sent?'] = get_request_status_links('status/sent', update['statuses'])
        row['refile?'] = get_request_status_links('status/refile', update['statuses'])
        row['portal?'] = get_request_status_links('status/portal', update['statuses'])
        row['replied?'] = get_request_status_links('replied', update['statuses'])
        row['attachment?'] = get_request_status_links('attachment', update['statuses'])
        row['denied?'] = get_request_status_links('status/denied', update['statuses'])
        row['appeal?'] = get_request_status_links('status/appeal', update['statuses'])
        new_report.append(row)
        print('updated',row['name'])
    outfile = open(status_report_path,'w')
    outcsv = csv.DictWriter(outfile,new_report[0].keys())
    outcsv.writeheader()
    for row in new_report:
        outcsv.writerow(row)
        print('writing',row)
    outfile.close()
    return new_report


def get_request_update(slug):
    """
    return [{request_slug:status},...]
    """
    try:
        statuses = get_statuses(slug)
        status = get_status(statuses)
        return {'status':status,'statuses':statuses}
    except Exception:
        return None


def slugify(row):
    """
    possibly redundant
    """
    return 'file/' + row['name'].replace(' ','_') + '/RID' + str(row['record_id'])


def get_sharepoint_status_report(wbid=workbook_id,tid=table_id):
    """
    assumes you've already posted a report
    in an excel workbook w/ a Table,
    returns the Table rows as {k:v} list
    """
    get_sheet_range_url = base_url + 'drive/items/{wbid}/workbook/worksheets/{wsid}/usedRange'.format(wbid=workbook_id,wsid=worksheet_id)
    sheet_data = json.loads(session.get(get_sheet_range_url,headers={'Content-Type':'application/json'}).content)
    return sheet_data


def _get_header(wbid,tid):
    """
    get headers from
    table column names
    """
    get_header_url = base_url + 'drive/items/' + workbook_id + '/workbook/tables/' + table_id + '/columns'
    columns = json.loads(session.get(get_header_url,headers={'Content-Type':'application/json'}).content)['value'] 
    return [x['name'] for x in columns]


def _get_rows(wbid,tid):
    """
    get records
    from table rows
    """
    table_rows_url = base_url + 'drive/items/' + wbid + '/workbook/tables/' + tid + '/rows'
    return json.loads(session.get(table_rows_url,headers={'Content-Type':'application/json'}).content)['value']
    

def patch_report():
    """
    call sharepoint with a patch to update excel file
    """
    # get the old sheet
    sheet_data = get_sharepoint_status_report()
    data_range = sheet_data['address']
    
    # update the data
    # zip headers=>rows
    headers = sheet_data['values'][0]
    rows = sheet_data['values'][1:]
    data = [dict(zip(headers,row)) for row in rows]
    updated_data = update_report(data)
    # gets confusing moving from indexed=>k:v=>index rows ... 
    updated_values = []
    updated_values.append(headers)
    for row in updated_data:
        updated_row = []
        for field in headers:
            updated_row.append(row[field])
        updated_values.append(updated_row)
    patch_payload = {'values': updated_values, 'formulas': sheet_data['formulas'], 'numberFormat': sheet_data['numberFormat']}
    patch_payload = {'values': updated_values, 'formulas': updated_values, 'numberFormat': sheet_data['numberFormat']}

    # clear the sheet
    clear_sheet()

    patch_sheet_url = base_url + "drive/items/{wbid}/workbook/worksheets/{wsid}/range(address='{address}')".format(wbid=workbook_id,wsid=worksheet_id,address=sheet_data['address'])

    patch_sheet_range = session.patch(patch_sheet_url,headers={'Content-Type':'application/json'},data=json.dumps(patch_payload))


def clear_sheet():
    session.post(base_url + 'drive/items/{wbid}/workbook/worksheets/{wsid}/range/clear'.format(wbid=workbook_id,wsid=worksheet_id),headers={'Content-Type':'application/json'})
