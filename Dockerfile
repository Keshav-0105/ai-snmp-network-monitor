FROM alpine:latest

WORKDIR /app

COPY snmp-monitor .
COPY data ./data

CMD ["./snmp-monitor"]

