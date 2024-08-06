#!/bin/bash

export YC_TOKEN=$(yc iam create-token)
export YC_CLOUD_ID=$(yc config get cloud-id)
export YC_FOLDER_ID=$(yc config get folder-id)
export YC_ZONE=$(yc config get compute-default-zone)
export TF_VAR_yc_folder_id=$YC_FOLDER_ID
export TF_VAR_yc_zone=$YC_ZONE