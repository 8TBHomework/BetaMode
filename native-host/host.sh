#!/bin/bash
cd -- "$(dirname "$0")" || exit 1
exec pipenv run python -m betamode
