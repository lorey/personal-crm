FROM python:3.8

WORKDIR /code
COPY Pipfile* /code/
RUN pip3 install pipenv
RUN pipenv install --dev

# all files to avoid missing files
# just makes containers a litte bigger
COPY . /code/
