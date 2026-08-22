FROM python:3-slim

COPY requirements.txt /websockettau/
RUN pip install --no-cache-dir -r /websockettau/requirements.txt

ADD *.py /websockettau/
ADD templates/* /websockettau/templates/
ADD static/* /websockettau/static/
ADD localhost.* /websockettau/
ADD chained.pem /websockettau/
ADD domain.key /websockettau/

WORKDIR /websockettau/
ENTRYPOINT [ "python", "./tau.py", "--debug", "--port=8000", "--ssl_port=8001" ]
