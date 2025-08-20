#!/bin/fish

set -g -x YC_TOKEN (yc iam create-token)
set -g -x YC_CLOUD_ID (yc config get cloud-id)
set -g -x YC_FOLDER_ID (yc config get folder-id)
set -g -x YC_ZONE (yc config get compute-default-zone)
set -g -x TF_VAR_yc_folder_id $YC_FOLDER_ID
set -g -x TF_VAR_yc_zone $YC_ZONE
set -g -x TF_VAR_tg_bot_token ""
set -g -x TF_VAR_tg_bot_secret ""
