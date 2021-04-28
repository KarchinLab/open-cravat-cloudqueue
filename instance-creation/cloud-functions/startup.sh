#!/bin/bash
ZONE=$(curl http://metadata.google.internal/computeMetadata/v1/instance/zone -H "Metadata-Flavor: Google")

ANNOTATORS=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/annotators -H "Metadata-Flavor: Google")

STAMP=`date +%s`

sleep 60

yum groupinstall -y "Development tools"

yum install -y python3 python3-devel

pip3 install --upgrade pip

python3 -m pip install --upgrade setuptools

pip3 install --upgrade firebase-admin


python3 - <<'END_SCRIPT'
from firebase_admin import firestore
db = firestore.Client()
doc_ref = db.collection(u'environment').document(u'imageStatus')
doc_ref.set({u'imageStatus' : "Creating"})
END_SCRIPT

pip3 install --upgrade open-cravat

oc module install-base
oc module install csvreporter
oc module install -y $ANNOTATORS

STAMP=$STAMP python3 - <<'END_SCRIPT'
from firebase_admin import firestore
import os
stamp = os.environ['STAMP']
db = firestore.Client()
doc_ref = db.collection(u'environment').document(u'imageTrigger')
doc_ref.update({u'imageTrigger' : stamp})
END_SCRIPT
