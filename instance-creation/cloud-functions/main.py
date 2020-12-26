import base64
import argparse
import os
import time
import random
import string
import googleapiclient.discovery
import json
from google.cloud import error_reporting
import logging
import sys
from google.cloud import firestore

def create_instance(event, context):
    resource_string = context.resource
    print(f"Function triggered by change to: {resource_string}.")
    print(str(event))
    db = firestore.Client()
    stat_ref = db.collection(u'environment').document(u'imageStatus')
    stat_ref.set({u'imageStatus' : "Launching"})
    env_ref = db.collection(u'environment').document(u'annotators')
    annolist = env_ref.get().get('annotators')
    annotators = ''
    for item in annolist:
        annotators += str(item)+' '    
    print(annotators)
    project = os.environ['GCP_PROJECT']
    compute = googleapiclient.discovery.build('compute', 'v1')
    image_check = compute.images().getFromFamily(
        project='centos-cloud', 
        family='centos-7',
    ).execute()
    region = os.environ['FUNCTION_REGION']
    zone = 'a'
    evzone = f'{region}-{zone}'
    source_disk_image = image_check['selfLink']
    machine_type = 'zones/' + evzone + '/machineTypes/n1-standard-1' 
    instance_name = "oc-source-instance"
    service_acct = os.environ['OCQ_SERVICE_ACCOUNT_EMAIL']
    startup = open(os.path.join(os.path.dirname(__file__), 'startup.sh'), 'r').read()
    config = {
        'name': instance_name,
        "serviceAccounts": [
            {
                "email": service_acct,
                "scopes": ["https://www.googleapis.com/auth/compute",
                           "https://www.googleapis.com/auth/devstorage.read_write",
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
                    'diskSizeGb': 300,
                }
            }
        ],
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [
                {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
            ]
        }],
        'metadata': {
            'items': [
                {
                    'key': 'annotators',
                    'value': annotators
                },
                {
                    'key': 'startup-script',
                    'value': startup
                },

                ]
            }
        }
    ret = compute.instances().insert(project=project,zone=evzone,body=config).execute()
    print("Launch:" + str(ret))
    return ret
