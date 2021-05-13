FROM python:3.8

WORKDIR /code
COPY requirements.* /code/
RUN pip install -r requirements.txt

# all files to avoid missing files
# just makes containers a litte bigger
COPY . /code/
