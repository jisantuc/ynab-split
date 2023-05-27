from python:3.10-slim

RUN mkdir -p /opt/src
WORKDIR /opt/src
COPY requirements.txt /opt/src/requirements.txt
COPY main.py /opt/src/main.py
RUN python3 -m pip install -r requirements.txt

ENTRYPOINT ["python3", "main.py"]
