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
COPY setup/server_setup.py \
     setup/create_worker_archive.py \
     setup/install_tools.py \
     setup/server_info.py.template \
     setup/retrieve_languages.py \
       /setup/setup/
RUN mkdir -p /setup/manager /setup/website
WORKDIR /setup
COPY ants/dist/ /setup/ants/dist/
RUN python setup/server_setup.py --take-over-server
