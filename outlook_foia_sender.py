import sys, json, csv, time, re, docx
import requests.exceptions
from azure.identity import ClientSecretCredential
from msgraphcore import GraphSession


### START CONFIG ###
config = json.load(open(sys.argv[1]))
foia_metadata_infile_path = 'foia_contacts.csv'
foia_template_infile_path = 'unarmed_foia_template.docx'
interval = 5 # seconds between requests
status_labels = ['sent','responded','attachment','installment','done','NA']
### END CONFIG ###


def init(graph_session):
    # read in foia metadata
    foia_metadata = read_in_foia_metadata()

    # create outlook contacts
    init_contacts(graph_session, foia_metadata)

    # create categories
    #init_categories(graph_session, foia_metadata)

    # send
    send(graph_session, foia_metadata)


def read_in_foia_metadata():
    infile_rows = [x for x in csv.DictReader(open(foia_metadata_infile_path))]
    metadata = dict()
    for row in infile_rows:
        buffer_row = {
                'person'   : row['name'],
                'date'     : row['date'],
                'location' : row['city'],
                'pd'       : row['police_department_name'],
                'emails'   : extract_emails(row['foia email(s)']),
                'slug'     : slugify(row)}
        if buffer_row['emails'] and buffer_row['person'] and buffer_row['slug']:
            metadata[row['record_id']] = buffer_row 
            print(metadata[row['record_id']])
    return metadata


def init_contacts(graph_session, foia_metadata):
    """
    might not need this yet
    """
    pass


def init_categories(graph_session, foia_metadata):
    print('   ***  generating status categories   ***   ')
    for status in status_labels:
        time.sleep(interval)
        try:
            response = graph_session.post('/users/' + config['sample_user'] + '/outlook/masterCategories',
                    data = json.dumps({"displayName":'status/' + status,"color":"preset10"}),
                    headers = {'Content-Type': 'application/json'})
            print(response, status)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(e)
    print('   ***   generating record categories   ***   ')
    for record_id in foia_metadata:
        record = foia_metadata[record_id]
        time.sleep(interval)
        try:
            response = graph_session.post('/users/' + config['sample_user'] + '/outlook/masterCategories',
                    data = json.dumps({"displayName":record['slug'],"color":"preset11"}),
                    headers = {'Content-Type': 'application/json'})
            print(response, record['slug'])
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(e)


def slugify(record):
    return 'file/' + record['name'].replace(' ','_').replace('.','') + '/RID' + record['record_id'] 


def extract_emails(text_blob):
    # how to split emails into lists
    rgx = r'[\w\.-]+@[\w\.-]+'
    return re.findall(rgx,text_blob)


def send(graph_session, foia_metadata):
    template = read_in_template()
    skip_ids = get_skip_ids(graph_session)
    for record_id in foia_metadata:
        if record_id in skip_ids:
            # don't spam
            print('skipping', record_id)
            continue
        record = foia_metadata[record_id]
        formatted_template = template.format(name=record['person'],date=record['date'],record_id=record_id)
        recipients = [{'emailAddress':{'address':address}} for address in record['emails']]
        categories = ['status/sent',record['slug']]
        body = {
            'message': {
                'subject': 'Public Records Request re ' + record['person'],
                'body': {
                    'contentType': 'Text',
                    'content': formatted_template
                },
                'toRecipients': recipients,
                'categories': categories}
        }
        try:
            response = graph_session.post('/users/' + config["sample_user"] + '/sendMail',
                data=json.dumps(body),
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
        time.sleep(interval)
        

def read_in_template():
    template = docx.Document(docx=foia_template_infile_path)
    return '\r\n'.join([p.text for p in template.paragraphs])


def kwarg_sub_template(text, record):
    return text.format(name=record['person'],date=record['date'],record_id=record['record_id'])


def compose_subject():
    pass
 

def get_skip_ids(graph_session):
    # idempotency, i.e. don't spam if things fail in mid-distro
    skip_ids = []
    paginate = True
    url = '/users/' + config['sample_user'] + '/messages'
    while paginate:
        response = graph_session.get(url)
        for skip_id in re.findall('RECORD_ID#\w+',response.text):
            skip_ids.append(skip_id.replace('RECORD_ID#',''))
        json_response = json.loads(response.content)
        if '@odata.nextLink' in json_response.keys():
            url = json_response['@odata.nextLink']
            continue
        else:
            return skip_ids
            


    

if __name__ == "__main__":

    # load params

    # authenticate
    credential = ClientSecretCredential(
        tenant_id = config["tenant_id"],
        client_id = config["client_id"],
        client_secret = config["client_secret"])

    # start a session
    graph_session = GraphSession(credential, config["scope"])

    # initialize
    init(graph_session)
