#!/bin/bash
set -x

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

execDir='/tmp/oc-job'
mkdir -p $execDir
cd $execDir

gsutil cp $INPUT .
gsutil cp $CONFIG .
oc run $FILENAME -c $CONFIGFILENAME -t csv 2>&1 | tee oc-cfrun-$STAMP-commandout.txt
outputDir="gs://$BUCKET/$BASEFILEPATH/$FILENAME-$STAMP/"
gsutil cp $FILENAME.sqlite $outputDir
gsutil cp $FILENAME.log $outputDir
gsutil cp $FILENAME.err $outputDir
gsutil cp $FILENAME.variant.csv $outputDir
gsutil cp oc-cfrun-$STAMP-commandout.txt $outputDir
msg="{\"jobId\":\"$JOB_ID\",\"dbPath\":\"$BASEFILEPATH/$FILENAME-$STAMP/$FILENAME.sqlite\"}"
echo msg
gcloud pubsub topics publish $DONETOPIC --message $msg
gsutil cp /var/log/messages $outputDir/
gcloud compute instances delete $(hostname) --quiet --zone=$ZONE
