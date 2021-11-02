#!/bin/bash
exec pipenv run -- uvicorn betamode:app "$@"
