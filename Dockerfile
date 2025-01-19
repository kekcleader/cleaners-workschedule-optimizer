FROM python:3.11-alpine

RUN apk update \
    && apk upgrade \
    && apk add --no-cache \
       bash \
       curl \
       openjdk17 \
       g++ \
       build-base \
       linux-headers \
       musl-dev \
       libffi-dev \
       openssl-dev

ENV JAVA_HOME="/usr/lib/jvm/java-17-openjdk"
ENV PATH="$JAVA_HOME/bin:$PATH"
ENV LD_LIBRARY_PATH="/usr/lib/jvm/java-17-openjdk/jre/lib/server"

RUN python3 -m venv /venv \
    && . /venv/bin/activate \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir optapy flask

ENV PATH="/venv/bin:$PATH"

#COPY program /program

WORKDIR /program
EXPOSE 5000
CMD ["python", "main.py"]
