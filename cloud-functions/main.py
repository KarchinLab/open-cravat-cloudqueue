import base64
import argparse
import os
import time
import random
import string
import googleapiclient.discovery
from google.cloud import pubsub_v1
import json
from google.cloud import error_reporting
import logging
import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore, storage
import yaml

cred = credentials.ApplicationDefault()
print(cred)
firebase_admin.initialize_app(cred)
db = firestore.Client()
subscriber = pubsub_v1.SubscriberClient()

def spawn_from_subscription():
    # TODO: use the firebase default bucket, not manually specified
    # TODO: ack messages that cause failure, otherwise system will get stuck
    bucket = storage.bucket(os.environ['OCQ_BUCKET'])
    evproject = os.environ['GCP_PROJECT']
    sub_name = os.environ['OCQ_JOB_START_SUB']
    subscription_path = subscriber.subscription_path(evproject, sub_name)
    print("Subscription:" + subscription_path)
    response = subscriber.pull({
        'subscription':subscription_path,
        'max_messages':1,
    })
    if not response.received_messages:
        print('No jobs to launch')
        return
    msg = response.received_messages[0]
    subscriber.modify_ack_deadline(request={
        'subscription':subscription_path,
        'ack_ids': [msg.ack_id],
        'ack_deadline_seconds':60
    })
    ack_id = msg.ack_id
    job_id = msg.message.data.decode('utf8')
    print("AckID:" + str(ack_id))
    print(f'JobID:{job_id}')
    job_document = db.collection('jobs').document(job_id)
    job_data = job_document.get().to_dict()
    run_config = {'run':{
        'genome': job_data['genome'],
        'skip': ['reporter'],
        'annotators': job_data['annotators'],
    }}
    config_blob = bucket.blob(f'jobs/{job_id}/config.yml')
    config_blob.upload_from_string(yaml.dump(run_config))
    filepath = job_data['inputPaths'][job_data['inputNames'][0]]
    configfilepath = config_blob.name
    basefilepath = configfilepath.rsplit('/', 1)[0]
    ocinput = 'gs://'+bucket.name + '/' + filepath
    occonfig = 'gs://'+bucket.name + '/' + configfilepath
    filename = filepath.rsplit('/', 1)[1]
    configfilename = configfilepath.rsplit('/', 1)[1]
    print("Bucket:" + bucket.name)
    print("Basefilepath:" + basefilepath)
    print("Inputs:" + ocinput)
    print("Filename:" + filename)
    print("Config:" + occonfig)
    print("Config Filename:" + configfilename)
    compute = googleapiclient.discovery.build('compute', 'v1')
    image_check = compute.images().getFromFamily(
        project=evproject, 
        family=os.environ['OCQ_INSTANCE_FAMILY'],
    ).execute()
    region = os.environ['FUNCTION_REGION']
    zone = 'a'
    evzone = f'{region}-{zone}'
    source_disk_image = image_check['selfLink']
    machine_type = 'zones/' + evzone + '/machineTypes/n1-standard-1' 
    instance_name = "oc-compute-instance-" + job_id.lower()
    service_acct = os.environ['OCQ_SERVICE_ACCOUNT_EMAIL']
    startup = open(os.path.join(os.path.dirname(__file__), 'startup.sh'), 'r').read()
    done_topic = os.environ['OCQ_JOB_DONE_TOPIC']
    worker_label = os.environ['OCQ_WORKER_LABEL']
    config = {
        'name': instance_name,
        "serviceAccounts": [
            {
                "email": service_acct,
                "scopes": ["https://www.googleapis.com/auth/compute",
                           "https://www.googleapis.com/auth/devstorage.read_write",
                           "https://www.googleapis.com/auth/pubsub",
                           "https://www.googleapis.com/auth/cloud-platform"
                        ]
            }
        ],
        'machineType': machine_type,
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                }
            }
        ],
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],
        'labels': {
            'instance_type': worker_label,
        },
        'metadata': {
            'items': [
                {
                    'key': 'ocinput',
                    'value': ocinput
                },
                {
                    'key': 'occonfig',
                    'value': occonfig
                },
                {
                    'key': 'bucket',
                    'value': bucket.name
                },
                {              
                    'key': 'filename',
                    'value': filename
                },
                {              
                    'key': 'configfilename',
                    'value': configfilename
                },
                {
                    'key': 'basefilepath',
                    'value': basefilepath
                },
                {
                    'key': 'subscription',
                    'value': subscription_path
                },
                {
                    'key': 'ack_id',
                    'value': ack_id
                },
                {
                    'key': 'startup-script',
                    'value': startup
                },
                {
                    'key': 'done_topic',
                    'value': done_topic
                },
                {
                    'key': 'job_id',
                    'value':job_id
                }
            ]
        }
    }
    ret = compute.instances().insert(project=evproject,zone=evzone,body=config).execute()
    print("Launch:" + str(ret))
    job_document.update({'status':{'code':20,'display':'Provisioning'}})
    return ret

def worker_space_available():
    # Return True if num workers is below limit
    evproject = os.environ['GCP_PROJECT']
    region = os.environ['FUNCTION_REGION']
    zone = 'a'
    evzone = f'{region}-{zone}'
    worker_label = os.environ['OCQ_WORKER_LABEL']
    compute = googleapiclient.discovery.build('compute', 'v1')
    cur_instances = compute.instances().list(project=evproject, zone=evzone).execute()
    if 'items' not in cur_instances:
        # No instances running of any type
        return True
    else:
        matching_instances = 0
        instance_limit = int(os.environ['OCQ_WORKER_LIMIT'])
        for instance in cur_instances['items']:
            instance_type = instance.get('labels',{}).get('instance_type')
            instance_status = instance.get('status')
            if instance_type == worker_label and instance_status in ('PROVISIONING', 'STAGING', 'RUNNING'):
                matching_instances += 1
        return matching_instances < instance_limit

def job_start(event, context):
    if worker_space_available():
        return spawn_from_subscription()
    else:
        print('Too many instances running')
        return

def job_done(event, context):
    evproject = os.environ['GCP_PROJECT']
    sub_name = os.environ['OCQ_JOB_DONE_SUB']
    subscription_path = subscriber.subscription_path(evproject, sub_name)
    print("Subscription:" + subscription_path)
    response = subscriber.pull({
        'subscription':subscription_path,
        'max_messages':1,
    })
    if not response.received_messages:
        print('No message to pull')
        return
    msg = response.received_messages[0]
    job_id = msg.message.data.decode('utf8')
    job_doc = db.collection('jobs').document(job_id)
    print(job_id, job_doc)
    job_doc.update({'status':{'code':40,'display':'Done'}})
    subscriber.acknowledge(subscription_path, [msg.ack_id])
    time.sleep(10)
    if worker_space_available():
        return spawn_from_subscription()
    else:
        print('Too many instances running')
        return

if __name__ == '__main__':
    import yaml
    with open('C:/a/gcloud/oc-cloudqueue/env.yml') as f:
        d = yaml.safe_load(f.read())
        os.environ.update(d)
    # spawn_from_subscription()
    # worker_space_available()
    job_done(None,None)