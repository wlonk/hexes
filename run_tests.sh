#!/bin/bash

set -e

if [[ $CIRCLECI ]]; then
    pyenv global 2.7.9 3.4.2
fi

tox
