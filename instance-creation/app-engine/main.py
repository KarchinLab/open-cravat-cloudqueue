# Copyright 2018 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
import datetime
from flask import Flask, render_template, request, redirect, url_for
from google.auth.transport import requests
from google.cloud import datastore
from google.cloud import storage
import google.oauth2.id_token
import sys
from google.cloud import pubsub_v1
import yaml
import requests

project_id = "oc-web-portal"
topic_name = "oc-task-queue"
bucket_name = "oc-webflow"

app = Flask(__name__)

firebase_request_adapter = google.auth.transport.requests.Request()
datastore_client = datastore.Client()
publisher = pubsub_v1.PublisherClient()

def fetch_new_list():
    #url = 'https://karchinlab.org/cravatstore/manifest.yml'
    url = 'http://localhost:8080/manifest.yml'
    data = requests.get(url)
    out = data.content
    currentvals = yaml.load(out, Loader=yaml.FullLoader)
    annolist = list()

    for i in currentvals.keys():
        if currentvals[i]['type'] == 'annotator':
            if (("chasmplus_" in str(i)) or ("segway_" in str(i))):
                pass
            else:
                annolist.append(i)
        else:
            pass

    return annolist

def create_anno_list(newannolist):
    newlist = newannolist
    configIn = {
        "run": { 
            "annotators": [ "clinvar", "go" ],
            "liftover": "hg38" ,
            "endat": "postaggregator",
        }
    }
    configOut = yaml.dump(configIn)
    yamlret = yaml.load(configOut, Loader=yaml.FullLoader)
    yamlret['run']['annotators'] = newlist
    with open('/tmp/config.yml', 'w') as file:
        yaml.dump(yamlret, file)
    client = storage.Client()
    bucket = client.get_bucket(bucket_name) 
    filename = '/tmp/config.yml'
    blob = bucket.blob("config.yml")
    blob.upload_from_filename(filename)

def create_db_anno_list(newannolist):
    newlist = newannolist
    client = datastore.Client()
    values = datastore.Entity(client.key('annolist', 'annolist'))
    values.update({
        'selected': newannolist,
        'isSet': True,
    })
    client.put(values)

def create_job_json(newannolist, configfile):
    newannolist = newannolist
    bucket_name = bucket_name
    configfile = configfile
    jobIn = """{
        "bucket": "oc-webflow",
        "inputs": [
            "1/xaa",
            "1/xab"
        ],
        "config": "1/config.yml",
        "annolist": [ "clinvar", "go" ]
    }
    """
    
    jobret = json.loads(jobIn)
    jobret['annolist'] = newannolist
    jobret['bucket'] = bucket_name
    jobret['configfile'] = configfile

    with open('/tmp/job.json', 'w') as file:
        yaml.dump(jobret,file)
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)
    filename = '/tmp/job.json'
    blob = bucket.blob("config.yml")
    blob.upload_from_filename(filename)

def pull_selected_annotators():
    query = datastore_client.query(kind='annolist')
    data = query.fetch(limit=1)
    results = list(data)
    isSet = None
    isSet = selections = results[0]['isSet']
    if isSet == True:
        selections = results[0]['selected']
        return(selections)
    else:
        print("You haven't chosen yet")

@app.route('/')
def root():
    id_token = request.cookies.get("token")
    error_message = None
    annolist = None
    claims = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            annolist = fetch_new_list()
        except ValueError as exc:
            error_message = str(exc)
    return render_template('index.html', error_message=error_message, user_data=claims, annolist=annolist)

@app.route('/manifest.yml', methods=['GET'])
def locallist():
    return redirect(url_for('static', filename='manifest.yml'))


@app.route('/check')
def check():
    id_token = request.cookies.get("token")
    userdetes = None
    error_message = None
    if id_token:
        try:
            userdetes = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)
        except ValueError as exc:
            error_message = str(exc)
    return render_template(
        'check.html',
        user_data=userdetes, error_message=error_message)


@app.route('/dispatch')
def dispatch():
    id_token = request.cookies.get("token")
    project_id = "oc-web-portal"
    topic_name = "oc-task-queue"
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)
    usercheck = None
    error_message = None
    if id_token:
        try:
            usercheck = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
        except ValueError as exc:
            error_message = str(exc)
        
        with open('job.json') as f:
            data = f.read()
            data = data.encode("utf-8")
            publisher.publish(topic_path, data=data)

        return render_template('dispatched.html')
    else:
        return render_template('index.html', error_message=error_message)

@app.route('/show_selected', methods=['POST'])
def get_anno_selections():
    if request.method == 'POST':
        annotators = request.get_json()
        annotrim = annotators['msoutput']
        create_anno_list(annotrim)			
    return render_template('list.html', annotators=annotators)


@app.route('/select_annotators', methods=['POST'])
def update_anno_selections():
    if request.method == 'POST':
        annotators = request.get_json()
        annotrim = annotators['msoutput']
        create_db_anno_list(annotrim)			
    return '', 204

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

