#!/bin/bash

if [ -n "${GCP_CREDENTIALS_JSON}" ]; then
  echo "${GCP_CREDENTIALS_JSON}" > ${GOOGLE_APPLICATION_CREDENTIALS}
else
  echo "GCP Service Account not provided, expected to run in GCP context"
fi

exec "$@"