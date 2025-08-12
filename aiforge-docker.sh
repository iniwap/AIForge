#!/bin/bash  
export PYTHONPATH=src  
export AIFORGE_LOCALE=${AIFORGE_LOCALE:-en}  
python -m aiforge.utils.manage_docker_services "$@"