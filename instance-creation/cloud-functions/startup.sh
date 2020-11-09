#!/bin/bash
ZONE=$(curl http://metadata.google.internal/computeMetadata/v1/instance/zone -H "Metadata-Flavor: Google")

ANNOTATORS=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/annotators -H "Metadata-Flavor: Google")

STAMP=`date +%s`

sleep 60

yum group install -y "Development tools"

yum install -y python3 python3-devel

pip3 install --upgrade google-cloud-firestore


python3 - <<'END_SCRIPT'
from google.cloud import firestore
db = firestore.Client()
doc_ref = db.collection(u'environment').document(u'imageStatus')
doc_ref.set({u'imageStatus' : "Creating"})
END_SCRIPT

pip3 install --upgrade open-cravat

oc module install-base

oc module install -y $ANNOTATORS

gcloud compute images create oc-runner-updated-$STAMP --force --family oc-runner-images --source-disk oc-source-instance --source-disk-zone $ZONE

python3 - <<'END_SCRIPT'
from google.cloud import firestore
db = firestore.Client()
doc_ref = db.collection(u'environment').document(u'imageStatus')
doc_ref.update({u'imageStatus' : "Ready"})
END_SCRIPT

gcloud compute instances delete $(hostname) --quiet --zone=$ZONE