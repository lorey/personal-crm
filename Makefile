.RECIPEPREFIX = >

.PHONY: all test format build up precommit
.FORCE:

all: test format precommit

test:
> docker-compose exec web ./manage.py test

format:
> docker-compose exec web isort --profile=black .
> docker-compose exec web black .
> sudo chown -R $(USER) networking
> sudo chown -R $(USER) networking_base
> sudo chown -R $(USER) networking_public
> sudo chown -R $(USER) networking_web
> sudo chown -R $(USER) *.py

lint:
> docker-compose exec web flake8 --ignore=E501,W503 .
> docker-compose exec web pylint networking_base networking_public networking_web || true

build: requirements.txt
> docker-compose build

# update requirements
requirements.txt: requirements.in
> docker-compose exec web pip-compile --upgrade
> sudo chown $(USER) requirements.txt

up:
> docker-compose up -d

precommit: build up test format lint
