# Copyright 2018 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
import datetime
from flask import Flask, render_template, request, redirect, flash, url_for
from functools import wraps
from google.auth.transport import requests
from google.cloud import storage
import firebase_admin
from firebase_admin import firestore, auth
import google.oauth2.id_token
import base64
import sys
from google.cloud import pubsub_v1
import yaml
import requests
import json
import random
import string
import time
import os

project_id = os.environ['GOOGLE_CLOUD_PROJECT']
topic_name = os.environ['OCQ_JOB_START_TOPIC']
bucket_name = os.environ['OCQ_BUCKET']
key_path = 'gcp-key.json' #Not in repo. Should change to get another way.
storage_client = storage.Client.from_service_account_json(key_path)
bucket = storage_client.get_bucket(bucket_name)
db = firestore.Client()


app = Flask(__name__)

firebase_request_adapter = google.auth.transport.requests.Request()

publisher = pubsub_v1.PublisherClient()
jobs_topic_path = publisher.topic_path(project_id, topic_name)

def access_control(admin):
    def user_login(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            id_token = request.cookies.get("token")
            if id_token: 
                try: 
                    google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
                    id_encoded = id_token.split('.')[1]+'='*5
                    id_data = json.loads(base64.b64decode(id_encoded))
                    doc_ref = db.collection(u'environment').document(u'authorized-users').get()
                    userrecord = doc_ref.to_dict()
                    authusers = userrecord["authorizedUsers"]
                    adminemail = authusers[0]
                    currentemail = id_data['email']
                    if (admin == True) and (currentemail == adminemail):
                        pass
                    elif (admin == False) and (currentemail in authusers):
                        pass
                    else:
                        return redirect('/')
                except ValueError:
                    return redirect('/')
                return f(*args, **kwargs)
            else:
                return redirect('/')
        return wrapper
    return user_login


def fetch_new_list():
    url = 'https://files.kylemoad.com/public/cravatstore/manifest.yml'
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

def create_db_anno_list(newannolist):
    newlist = newannolist
    doc_ref = db.collection(u'environment').document(u'annotators')
    doc_ref.update({u'annotators': newlist})

@app.route('/')
def root():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    times = None
    annolist = None

    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            annolist = fetch_new_list()
        except ValueError as exc:
            error_message = str(exc)
    return render_template(
        'index.html',
        user_data=claims, error_message=error_message, annolist=annolist)

@app.route('/submit')
@access_control(admin=False)
def index():
    id_token = request.cookies.get("token")
    try:
        google.oauth2.id_token.verify_firebase_token(
            id_token, firebase_request_adapter)
    except ValueError:
        return redirect('/')
    return render_template('submit.html')

@app.route('/admin')
@access_control(admin=True)
def admin():
    annolist = None
    id_token = request.cookies.get("token")
    try:
        google.oauth2.id_token.verify_firebase_token(
            id_token, firebase_request_adapter)
        annolist = fetch_new_list()
    except ValueError:
        #return redirect('/')
        return render_template('admin.html', annolist=annolist)

    return render_template('admin.html', annolist=annolist)

@app.route('/show_selected', methods=['POST'])
@access_control(admin=False)
def get_anno_selections():
    if request.method == 'POST':
        annotators = request.get_json()
        annotrim = annotators['msoutput']
        create_db_anno_list(annotrim)			
    return ('',200)

def new_job_id():
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(10))

@app.route('/init-job',methods=['POST'])
@access_control(admin=False)
def init_job():
    input_files = request.json['inputFiles']
    job_id = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
    status_obj = bucket.blob(f'jobs/{job_id}/status.json')
    while status_obj.exists():
        job_id = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
        status_obj = bucket.blob(f'jobs/{job_id}/status.json')
    status_obj.upload_from_string(json.dumps({'status':'initialized'}))
    ret = {'id':job_id,'inputs':{}}
    for fn in input_files:
        fid = f'jobs/{job_id}/{fn}'
        obj = bucket.blob(fid)
        url = obj.generate_signed_url(
            method='PUT',
            expiration=int(time.time()+3600),
        )
        ret['inputs'][fn] = {
            'name':obj.name,
            'url':url
        }
    print(f'initialized {job_id}')
    return ret

def enqueue_job(job_id):
    publisher.publish(
        jobs_topic_path, 
        data=job_id.encode('utf-8')
    )

@app.route('/submit-job',methods=['POST'])
@access_control(admin=False)
def submit_job():
    data = request.json
    job_id = data['jobId']
    enqueue_job(job_id)
    return ('',200)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
