FROM eclipse-mosquitto:2.0.22
USER root
RUN apk add --no-cache openssl
COPY mosquitto.conf /mosquitto/config/mosquitto.conf
COPY acl /mosquitto/config/acl
COPY start.sh /usr/local/bin/sentinel-start
ENTRYPOINT ["sh", "/usr/local/bin/sentinel-start"]
