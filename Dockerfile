FROM python:2

RUN apt update && \
    apt install -y \
      python-mysqldb \
      make \
      git \
      cron \
      unzip \
      sudo \
      memcached \
      php-memcache \
      zip \
      nodejs \
      cvs \
      openjdk-11-jdk \
      ant \
      python-setuptools \
      dvipng \
      texlive-latex-base
RUN curl -sL https://deb.nodesource.com/setup_12.x | sudo -E bash - && \
    apt install -y nodejs
COPY . /setup/
WORKDIR /setup
RUN python setup/server_setup.py --take-over-server
CMD python worker/worker.py -t -n 0
