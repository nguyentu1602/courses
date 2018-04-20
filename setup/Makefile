SHELL=/bin/bash
CONDAENV=py27_tf_cv
CURDIR := $(notdir $(shell pwd))

sacfcv:
	source activate $(CONDAENV)

exportenv:
	source activate $(CONDAENV) && sleep 5 && conda env export | grep -v "^prefix: " > env_$(CONDAENV)_new.yml

testtf:
	source activate $(CONDAENV) && python tf_env_test.py

