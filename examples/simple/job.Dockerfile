# syntax=docker/dockerfile:experimental

FROM python:3.9.9-buster

# Check context
ADD train.py .
