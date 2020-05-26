FROM python:3.8

RUN mkdir -p /home/nimbus/store/data/volume
RUN mkdir /home/nimbus/store/app
RUN pip install pipenv
COPY Pipfile /tmp
RUN cd /tmp && pipenv lock --requirements > requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY . /home/nimbus/store

WORKDIR /home/nimbus/store
EXPOSE 4242

CMD python3 start.py /home/nimbus/store/data/volume /home/nimbus/store/data/db.sqlite -m
