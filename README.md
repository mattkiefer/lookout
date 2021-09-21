# lookout
lookout = [foiamail](https://github.com/bettergov/foiamail) + [outlook](https://docs.microsoft.com/en-us/graph/overview)
![foiamail art by lucas ian smith](https://github.com/mattkiefer/lookout/blob/main/foiamail.jpeg)


## track + manage mass foia campaigns
Lookout was designed for newsrooms that need to do large-scale public records requests using Outlook for mail and MS OneDrive for file management. It's open-source software that's been deployed in production but it's still beta and needs more QA and documentation. Please feel free to try this out, fix any bugs you find and submit a pull request. Feature suggestions welcome.

Lookout does three things:
- distributes public records requests
- tracks email responses
- organizes file attachments

Lookout hooks into Outlook, Excel, OneDrive and other [MS Graph APIs](https://docs.microsoft.com/en-us/graph/api/overview?view=graph-rest-1.0).

Need something like this that works with Gmail, Sheets and Drive? Try [FOIAmail](https://github.com/bettergov/foiamail).

Need something with a web interface or more features? Try [MuckRock](https://muckrock.com).

## technical overview
Lookout calls MS Graph APIs using Python and a few command-line tools. It's pretty minimalist. For your part, you'll want to bring 
- a Microsoft account 
- an Azure app 
- a template records request
- a list of contacts.

You'll configure these things in the config directory.

### getting started
- set up a MS user
- set up a managed Azure app with scopes to
    - read/write mail
    - read/write files
- clone this repo
- pip install requirements
    - `pip install -i https://test.pypi.org/simple/ msgraphcore`
    - `pip install azure-identity`
    - `pip install -r requirements.txt`
- enter your user/apps secrets in the config directory
- enter your project-specific configs there, too


### distributing mail
TK

### recurring jobs
Currently, Lookout has two recurring tasks:
- updating the status report
- moving attachments

The status report runs via the `patch_report()` function in reports/status.py

The attachments move via the `sweep()` function in att/att.py
