FROM python:3.8

RUN mkdir -p /home/nimbus/store/data
RUN mkdir /home/nimbus/store/volume
RUN mkdir /home/nimbus/store/app
RUN pip install poetry
COPY poetry.lock pyproject.toml /home/nimbus/store/app/
RUN cd /home/nimbus/store/app && poetry config virtualenvs.create false && poetry install -n
COPY start.py /home/nimbus/store/app
COPY src /home/nimbus/store/app/src
COPY db /home/nimbus/store/app/db

WORKDIR /home/nimbus/store/app
EXPOSE 4242

CMD python3 start.py /home/nimbus/store/volume /home/nimbus/store/data/db.sqlite -m
