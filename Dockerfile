FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    make \
    python3 \
    python3-pip

COPY . /pi_weather

WORKDIR /pi_weather

RUN make setup-server-local

CMD ["make", "run-server-local"]
