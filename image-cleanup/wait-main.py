import os
import time
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from google.cloud import firestore

def shut_instance(compute, project, zone, instance_name):
    return compute.instances().stop(
        project=project,
        zone=zone,
        instance=instance_name).execute()

def delete_instance(compute, project, zone, instance_name):
    return compute.instances().delete(
        project=project,
        zone=zone,
        instance=instance_name).execute()

def create_image(compute, project, zone, instance_name):
    seconds = str(int(time.time()))
    imageName = "oc-runner-updated" + seconds
    sourceDisk = "https://www.googleapis.com/compute/v1/projects/" + project + "/zones/" + zone + "/disks/" + instance_name
    image_body = {
        "name": imageName,
        "sourceDisk": sourceDisk,
        "family": "oc-runner-images",
    }
    request = compute.images().insert(project=project, body=image_body)
    response = request.execute()
    return response

def change_status():
    db = firestore.Client()
    doc_ref = db.collection(u'environment').document(u'imageStatus')
    doc_ref.update({u'imageStatus' : "Ready"})


def wait_for_operation(compute, project, zone, operation):
    print('Waiting for operation to finish...')
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation).execute()

        if result['status'] == 'DONE':
            print("done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(1)

def wait_for_global_operation(compute, project, operation):
    print('Waiting for operation to finish...')
    while True:
        result = compute.globalOperations().get(
            project=project,            
            operation=operation).execute()

        if result['status'] == 'DONE':
            print("done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(1)

def main(event, context, wait=True):
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)
    project = os.environ['GCP_PROJECT']
    region = os.environ['FUNCTION_REGION']
    subzone = 'a'
    zone = f'{region}-{subzone}'
    instance_name = 'oc-source-instance'
    time.sleep(30)

    operation = shut_instance(compute, project, zone, instance_name)
    wait_for_operation(compute,project,zone,operation['name'])

    operation = create_image(compute, project, zone, instance_name)
    wait_for_global_operation(compute, project, operation['name'])

    operation = delete_instance(compute, project, zone, instance_name)
    wait_for_operation(compute, project, zone, operation['name'])

    change_status()

