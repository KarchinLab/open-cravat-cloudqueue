#!/bin/bash

eval $(bash parseyaml.sh env.yml)

gcloud config set project $GCP_PROJECT
OCQ_SERVICE_ACCOUNT_EMAIL="$OCQ_SERVICE_ACCOUNT_NAME@$GCP_PROJECT.iam.gserviceaccount.com"

# Functions
gcloud functions delete $OCQ_JOB_START_FUNC --quiet
gcloud functions delete $OCQ_JOB_DONE_FUNC --quiet
gcloud functions delete $OCQ_INSTANCE_CREATE_FUNC --quiet
gcloud functions delete $OCQ_IMAGE_CREATE_FUNC --quiet


# Subscriptions
gcloud pubsub subscriptions delete $OCQ_JOB_START_SUB
gcloud pubsub subscriptions delete $OCQ_JOB_DONE_SUB
gcloud pubsub subscriptions delete $OCQ_INSTANCE_CREATE_FUNC

# Topics
gcloud pubsub topics delete $OCQ_JOB_START_TOPIC
gcloud pubsub topics delete $OCQ_JOB_DONE_TOPIC

# Service Account
gcloud iam service-accounts delete $OCQ_SERVICE_ACCOUNT_EMAIL --quiet

# App Engine
echo Disable App Engine at https://console.cloud.google.com/appengine/settings?project=$GCP_PROJECT