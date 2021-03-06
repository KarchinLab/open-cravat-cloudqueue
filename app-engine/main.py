# Copyright 2018 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
import datetime
from flask import Flask, render_template, request, redirect, flash, url_for, send_from_directory
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
import datetime as dt

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
                    is_admin = currentemail == adminemail
                    kwargs['is_admin'] = is_admin
                    is_user = currentemail in authusers
                    kwargs['is_user'] = is_user
                    if admin and not is_admin:
                        return redirect('/')
                    if not(admin) and not is_user:
                        return redirect('/')
                except ValueError:
                    return redirect('/')
                return f(*args, **kwargs)
            else:
                return redirect('/')
        return wrapper
    return user_login

def fetch_manifest():
    mani_ref = db.collection('environment').document('manifest')
    mani_doc = mani_ref.get()
    if mani_doc.exists and dt.datetime.now(dt.timezone.utc) - mani_doc.update_time < dt.timedelta(hours=24):
        manifest = mani_doc.to_dict()
    else:
        print('from source')
        url = 'https://store.opencravat.org/manifest.yml'
        data = requests.get(url)
        out = data.content
        manifest = yaml.load(out, Loader=yaml.FullLoader)
        mani_ref.set(manifest)
    return manifest

def fetch_new_list():
    manifest = fetch_manifest()
    annolist = list()
    for i in manifest.keys():
        if manifest[i]['type'] == 'annotator':
            if (("chasmplus_" in str(i)) or ("segway_" in str(i))):
                pass
            else:
                annolist.append(i)
        else:
            pass
    return sorted(annolist)

@app.route('/manifest')
def manifest():
    return fetch_manifest()

@app.route('/markdown')
def markdown():
    mname = request.args.get('module')
    version = request.args.get('version')
    mdoc_ref = db.collection('environment').document('manifest').collection('module-doc').document(mname)
    mdoc = mdoc_ref.get()
    md_text = None
    if mdoc.exists and dt.datetime.now(dt.timezone.utc) - mdoc.update_time < dt.timedelta(hours=24):
        md_text = mdoc.to_dict().get('data')
    if md_text is None:
        url = f'https://store.opencravat.org/modules/{mname}/{version}/{mname}.md'
        r = requests.get(url)
        r.raise_for_status()
        md_text = r.text
        mdoc_ref.set({'data':md_text})
    return md_text

def create_db_anno_list(newannolist):
    newlist = newannolist
    doc_ref = db.collection(u'environment').document(u'annotators')
    doc_ref.update({u'annotators': newlist})

@app.route('/')
def root():
    return render_template('index.html')

@app.route('/submit')
@access_control(admin=False)
def submit(is_admin=False, **kwargs):
    return render_template('submit.html', is_user=True, is_admin=is_admin)

@app.route('/admin')
@access_control(admin=True)
def admin(**kwargs):
    annolist = fetch_new_list()
    return render_template('admin.html', is_user=True, is_admin=True, annolist=annolist)

@app.route('/show_selected', methods=['POST'])
@access_control(admin=True)
def get_anno_selections(**kwargs):
    if request.method == 'POST':
        annotators = request.get_json()
        annotrim = annotators['msoutput']
        create_db_anno_list(annotrim)			
    return ('',200)

def new_job_id():
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(10))

@app.route('/init-job',methods=['POST'])
@access_control(admin=False)
def init_job(**kwargs):
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
def submit_job(**kwargs):
    data = request.json
    job_id = data['jobId']
    enqueue_job(job_id)
    return ('',200)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
