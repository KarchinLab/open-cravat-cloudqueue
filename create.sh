#!/bin/bash
set -e

# Read in project-wide environment variables
python3 makeenv.py config.yml
eval $(bash parseyaml.sh env.yml)

if gcloud projects list --format flattened $project | grep -Eq "projectId:\s+$GCP_PROJECT"
then
    echo Project found
else
    echo Creating project
    gcloud projects create $GCP_PROJECT
fi
gcloud config set project $GCP_PROJECT
echo 'Billing Accounts:'
gcloud beta billing accounts list --filter open=true | tr -s ' ' | cut -d ' ' -f 2 | tail -n +2
read -p "Enter a billing account for this project from the list above: " billingAccountName
# billingAccountId=$(gcloud beta billing accounts list --filter displayName=$billingAccountName --limit 1 | tail -n +2 | cut -f1 -d' ')
# gcloud beta billing projects link $GCP_PROJECT --billing-account=$billingAccountId

echo 'Enabling cloudfunction and cloudbuild APIs'
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Service account
OCQ_SERVICE_ACCOUNT_EMAIL="$OCQ_SERVICE_ACCOUNT_NAME@$GCP_PROJECT.iam.gserviceaccount.com"
sacctKey='app-engine/gcp-key.json'
echo "Creating service account $OCQ_SERVICE_ACCOUNT_NAME with editor role"
# gcloud iam service-accounts create "$OCQ_SERVICE_ACCOUNT_NAME" --description "$OCQ_SERVICE_ACCOUNT_DESC" --display-name "$OCQ_SERVICE_ACCOUNT_DISPLAY"
# gcloud projects add-iam-policy-binding $GCP_PROJECT --member "serviceAccount:$OCQ_SERVICE_ACCOUNT_EMAIL" --role 'roles/editor'
gcloud iam service-accounts keys create --iam-account $OCQ_SERVICE_ACCOUNT_EMAIL $sacctKey
export GOOGLE_APPLICATION_CREDENTIALS="$sacctKey"

# Firebase
echo "This tool uses Firebase to provide authentication, database management, and cloud storage."
echo "Unfortunately, many Firebase services cannot be initialized without user input."
echo "You will be directed to enable some Firebase services in a browser, and to reply to some command line prompts."
read -p "Press enter to continue"
rm -f .firebaserc
#TODO add firebase only if not already added
# firebase projects:addfirebase $GCP_PROJECT
firebase use $GCP_PROJECT
sdkCmd=$(firebase apps:create web ocq | grep 'firebase apps:sdkconfig WEB .*$' -o)
$sdkCmd > app-engine/static/firebase-config.js

# Authentication
echo "Open the link below and enable Email/Password authentication. Do not enable Email link authentication"
echo "https://console.firebase.google.com/u/0/project/$GCP_PROJECT/authentication/providers"
read -p "Press enter to continue"

# Firestore
echo "Open the link below and create a firestore database with the default settings"
echo "https://console.firebase.google.com/project/$GCP_PROJECT/firestore"
read -p "Press enter to continue"
echo "Deploying firestore database configuration"
echo "Follow the prmpts to accept the default paths for firestore.rules and firestore.indexes.json. Do not overwrite the files."
read -p "Press enter to continue"
firebase init firestore
echo "Deploy initial data to firestore"
#TODO this is hanging
python3 initdb.py

# Cloud storage
echo "Deploying cloud storage configuration"
echo "Follow the prompts to accept the default path for storage.rules"
firebase init storage
firebase deploy

# PubSub
echo "Deploying pubsub message queues"
gcloud pubsub topics create $OCQ_JOB_START_TOPIC
gcloud pubsub subscriptions create $OCQ_JOB_START_SUB --topic $OCQ_JOB_START_TOPIC --ack-deadline 60
gcloud pubsub topics create $OCQ_JOB_DONE_TOPIC
gcloud pubsub subscriptions create $OCQ_JOB_DONE_SUB --topic $OCQ_JOB_DONE_TOPIC --ack-deadline 60

# Cloud functions
#TODO add region to functions (probably to everything else too)
echo 'Deploying functions'
gcloud beta functions deploy $OCQ_INSTANCE_CREATE_FUNC \
    --source=instance-creation/cloud-functions/ \
    --runtime=python38 \
    --entry-point create_instance \
    --service-account $OCQ_SERVICE_ACCOUNT_EMAIL \
    --memory=256MB \
    --trigger-event=providers/google.firebase.database/eventTypes/ref.update \
    --trigger-resource="projects/$GCP_PROJECT/databases/(default)/documents/environment/annotators" \
    --env-vars-file env.yml
gcloud functions deploy $OCQ_JOB_START_FUNC \
    --source cloud-functions/ \
    --runtime python38 \
    --entry-point job_start \
    --service-account $OCQ_SERVICE_ACCOUNT_EMAIL \
    --env-vars-file env.yml \
    --trigger-topic $OCQ_JOB_START_TOPIC \
    --max-instances 1
gcloud functions deploy $OCQ_JOB_DONE_FUNC \
    --source cloud-functions/ \
    --runtime python38 \
    --entry-point job_start \
    --service-account $OCQ_SERVICE_ACCOUNT_EMAIL \
    --env-vars-file env.yml \
    --trigger-topic $OCQ_JOB_DONE_TOPIC \
    --max-instances 1

echo 'Deploying app'
gcloud app deploy app-engine