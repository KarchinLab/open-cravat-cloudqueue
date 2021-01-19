#!/bin/bash
set -e

#Oyaml required for early step and firestore needed for db manipulation
read -p "We need to install a couple of pip packages (oyaml, and google-cloud-firestore) to make this deployment work. Are you ok with this change to your environment? (Please enter 'y' to confirm)" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    pip3 install oyaml google-cloud-firestore
else
    echo "Please consider using a python virtual environment if you can't modify your system python"
fi


# Read in project-wide environment variables
python3 makeenv.py config.yml
eval $(bash parseyaml.sh env.yml)

# Create project if it does not exist
echo "Checking for project $GCP_PROJECT"
if gcloud projects list --format flattened $project | grep -Eq "projectId:\s+$GCP_PROJECT"
then
    echo "Project found"
else
    echo "Creating new project $GCP_PROJECT"
    gcloud projects create $GCP_PROJECT
fi
gcloud config set project $GCP_PROJECT > /dev/null 2>&1

echo 'Checking for billing account'
if $(gcloud beta billing projects describe $GCP_PROJECT | grep 'billingEnabled: true' -q); 
then
    echo "Billing account found"
else
    echo 'Billing account required'
    declare -A accountNames
    acctNum=1
    firstIter=true
    while read line
    do
        if [[ $firstIter == true ]]
        then
            echo 'Available billing accounts'
            firstIter=false
        fi
        displayPattern='displayName:\s+(.*)'
        namePattern='name:\s+(.*)'
        if [[ $line =~ '---' ]]
        then
            displayName=
            name=
            assigned=false
        elif [[ $line =~ $displayPattern ]]
        then
            displayName=${BASH_REMATCH[1]}
        elif [[ $line =~ $namePattern ]]
        then
            name=${BASH_REMATCH[1]}
        fi
        if [[ $assigned != true && -n $displayName && -n $name ]]
        then
            echo "    [$acctNum]    $displayName"
            accountNames[$acctNum]=$name
            assigned=true
            acctNum=$((acctNum+1))
        fi        
    done <<< $(gcloud beta billing accounts list --filter open=true --format flattened)
    while true
    do
        read -p "Account number: " selAcctNum
        billingAccountId=${accountNames[$selAcctNum]}
        if [[ -n $billingAccountId ]]
        then
            break
        else
            echo "Invalid"
        fi
    done
    echo "Linking billing account to project"
    gcloud beta billing projects link $GCP_PROJECT --billing-account=$billingAccountId
fi

echo 'Enabling cloudfunction and cloudbuild APIs'
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com

echo 'Enabling the Firebase API'
gcloud services enable firebase.googleapis.com

# Service account
OCQ_SERVICE_ACCOUNT_EMAIL="$OCQ_SERVICE_ACCOUNT_NAME@$GCP_PROJECT.iam.gserviceaccount.com"
sacctKey='app-engine/gcp-key.json'
echo "Creating service account $OCQ_SERVICE_ACCOUNT_NAME with editor role"
# gcloud iam service-accounts create "$OCQ_SERVICE_ACCOUNT_NAME" --description "$OCQ_SERVICE_ACCOUNT_DESC" --display-name "$OCQ_SERVICE_ACCOUNT_DISPLAY"
# gcloud projects add-iam-policy-binding $GCP_PROJECT --member "serviceAccount:$OCQ_SERVICE_ACCOUNT_EMAIL" --role 'roles/editor'
# gcloud iam service-accounts keys create --iam-account $OCQ_SERVICE_ACCOUNT_EMAIL $sacctKey
export GOOGLE_APPLICATION_CREDENTIALS="$sacctKey"

# Firebase
cat << EOF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This tool uses Firebase to provide authentication, database management, and 
cloud storage. Unfortunately, many Firebase services cannot be initialized 
without user input. You will be directed to enable some Firebase services in a 
browser, and to reply to some command line prompts.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
EOF
read -p "Press enter to continue"
rm -f .firebaserc
#TODO add firebase only if not already added
# firebase projects:addfirebase $GCP_PROJECT
firebase use $GCP_PROJECT
sdkCmd=$(firebase apps:create web ocq | grep 'firebase apps:sdkconfig WEB .*$' -o)
$sdkCmd > app-engine/static/firebase-config.js

# Authentication
cat << EOF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Open the link below, and enable Email/Password authentication. 
Do not enable Email link authentication.
https://console.firebase.google.com/u/0/project/$GCP_PROJECT/authentication/providers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
EOF
read -p "Press enter to continue"

# Firestore
cat << EOF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Open the link below, and create a Firestore database with the default settings.
https://console.firebase.google.com/project/$GCP_PROJECT/firestore
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
EOF
read -p "Press enter to continue"
cat << EOF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Deploying firestore database configuration.
Follow the prmpts to accept the default paths for firestore.rules and 
firestore.indexes.json. Do not overwrite the files.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
EOF
read -p "Press enter to continue"
firebase init firestore
echo "Deploy initial data to firestore"
python3 initdb.py

# Cloud storage
echo "Deploying cloud storage configuration"
cat << EOF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Follow the prompts to accept the default path for storage.rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
EOF
read -p "Press enter to continue"
firebase init storage
firebase deploy

# PubSub
echo "Deploying pubsub message queues"
gcloud pubsub topics create $OCQ_JOB_START_TOPIC
gcloud pubsub subscriptions create $OCQ_JOB_START_SUB --topic $OCQ_JOB_START_TOPIC --ack-deadline 60
gcloud pubsub topics create $OCQ_JOB_DONE_TOPIC
gcloud pubsub subscriptions create $OCQ_JOB_DONE_SUB --topic $OCQ_JOB_DONE_TOPIC --ack-deadline 60

# Cloud functions
echo 'Deploying functions'
gcloud beta functions deploy $OCQ_INSTANCE_CREATE_FUNC \
    --source=instance-creation/cloud-functions/ \
    --runtime=python38 \
    --entry-point create_instance \
    --service-account $OCQ_SERVICE_ACCOUNT_EMAIL \
    --memory=256MB \
    --trigger-event=providers/cloud.firestore/eventTypes/document.update \
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

appURL=$(gcloud app browse --no-launch-browser)
cat << EOF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Deployment finished. Open the link to create an administrator account with the
email below. Then use the admin page to create an annotation worker image. When 
the worker image is finished, users may create accounts and submit jobs.
Administrator email: $OCQ_ADMIN_EMAIL
App URL: $appURL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
EOF