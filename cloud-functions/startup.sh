#!/bin/bash
INPUT=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/ocinput -H "Metadata-Flavor: Google")
CONFIG=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/occonfig -H "Metadata-Flavor: Google")
BUCKET=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/bucket -H "Metadata-Flavor: Google")
BASEFILEPATH=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/basefilepath -H "Metadata-Flavor: Google")
FILENAME=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/filename -H "Metadata-Flavor: Google")
CONFIGFILENAME=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/configfilename -H "Metadata-Flavor: Google")
ZONE=$(curl http://metadata.google.internal/computeMetadata/v1/instance/zone -H "Metadata-Flavor: Google")
ACK_ID=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/ack_id -H "Metadata-Flavor: Google")
SUBSCRIPTION=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/subscription -H "Metadata-Flavor: Google")
DONETOPIC=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/done_topic -H "Metadata-Flavor: Google")
JOB_ID=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/job_id -H "Metadata-Flavor: Google")

gcloud pubsub subscriptions ack $SUBSCRIPTION --ack-ids=$ACK_ID


STAMP=`date +%s`

cd /tmp

gsutil cp $INPUT .
gsutil cp $CONFIG .
cravat /tmp/$FILENAME -c /tmp/$CONFIGFILENAME 2>&1 | tee oc-cfrun-$STAMP-commandout.txt
gsutil cp $FILENAME.sqlite $BUCKET/$BASEFILEPATH/$FILENAME-$STAMP/
gsutil cp $FILENAME.log $BUCKET/$BASEFILEPATH/$FILENAME-$STAMP/
gsutil cp $FILENAME.err $BUCKET/$BASEFILEPATH/$FILENAME-$STAMP/
gsutil cp oc-cfrun-$STAMP-commandout.txt $BUCKET/$BASEFILEPATH/$FILENAME-$STAMP/
gsutil cp /var/log/messages $BUCKET/$BASEFILEPATH/$FILENAME-$STAMP/
gcloud pubsub topics publish $DONETOPIC --message $JOB_ID
gcloud compute instances delete $(hostname) --quiet --zone=$ZONE
