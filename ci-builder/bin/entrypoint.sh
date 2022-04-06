#!/bin/bash

if [ -n "${GCP_CREDENTIALS_JSON}" ]; then
  echo "${GCP_CREDENTIALS_JSON}" > ${GOOGLE_APPLICATION_CREDENTIALS}
else
  echo "GCP Service Account not provided, did you set GCP_CREDENTIALS_JSON?"
  exit 1
fi

exec "$@"