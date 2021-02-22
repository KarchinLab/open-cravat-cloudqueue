import os
import time
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from google.cloud import firestore
from multiprocessing import Process

def create_image(event, context):
  time.sleep(60)
  credentials = GoogleCredentials.get_application_default()
  project = os.environ['GCP_PROJECT']
  region = os.environ['FUNCTION_REGION']
  zone = 'a'
  evzone = f'{region}-{zone}'
  seconds = str(int(time.time()))
  imageName = "oc-runner-updated" + seconds
  sourceDisk = "https://www.googleapis.com/compute/v1/projects/" + project + "/zones/" + evzone + "/disks/oc-source-instance"
  service = discovery.build('compute', 'v1', credentials=credentials)
  image_body = {
    "name": imageName,
    "sourceDisk": sourceDisk,
    "family": "oc-runner-images",
  }
  request = service.images().insert(project=project, body=image_body)
  response = request.execute()
  spawn = Process(delete_instance(service, project, evzone, 'oc-source-instance'))
  spawn.start()
  return response

def change_status():
  db = firestore.Client()
  doc_ref = db.collection(u'environment').document(u'imageStatus')
  doc_ref.update({u'imageStatus' : "Ready"})

def delete_instance(compute, project, zone, name):
  time.sleep(400)
  change_status()
  return compute.instances().delete(
      project=project,
      zone=zone,
      instance=name).execute()