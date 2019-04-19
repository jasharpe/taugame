FROM python:2

RUN pip install tornado==4.0.2 backports.ssl_match_hostname sqlalchemy

ADD *.py /websockettau/
ADD templates/* /websockettau/templates/
ADD static/* /websockettau/static/
ADD localhost.* /websockettau/

WORKDIR /websockettau/
CMD [ "python", "./tau.py", "--debug", "--port=8000", "--ssl_port=8001" ]
