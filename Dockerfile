FROM ubuntu:22.04

ENV IS_DOCKER=1

RUN apt-get update && apt-get install -y \
    make \
    python3 \
    python3-pip

COPY requirements-server.txt /pi_weather/requirements-server.txt

RUN pip3 install -r /pi_weather/requirements-server.txt

COPY . /pi_weather

WORKDIR /pi_weather

CMD ["make", "run-server-local"]
