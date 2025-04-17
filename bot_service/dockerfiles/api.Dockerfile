FROM python:3.11.5
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt /app/requirements.txt
RUN pip install --disable-pip-version-check --no-cache-dir --no-input --quiet --requirement /app/requirements.txt
RUN apt-get update -y
COPY src /app
WORKDIR /app
USER root
# provide env file path to runner 
CMD ["/bin/bash", "-c", "python3 runner_api -e ./etc/.env "]
# CMD ["/bin/bash", "-c", "python3 runner -e ./etc/.env.new"]