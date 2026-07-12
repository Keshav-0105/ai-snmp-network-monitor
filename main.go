package main

import (
	"fmt"
	"log"
	"time"

	"github.com/gosnmp/gosnmp"
)

func main() {
	snmp := &gosnmp.GoSNMP{
		Target:    "127.0.0.1",
		Port:      1161,
		Community: "public",
		Version:   gosnmp.Version2c,
		Timeout:   time.Duration(2) * time.Second,
		Retries:   3,
	}

	err := snmp.Connect()
	if err != nil {
		log.Fatalf("Connect error: %v", err)
	}
	defer snmp.Conn.Close()

	oids := []string{
		"1.3.6.1.2.1.25.3.3.1.2.1",
		"1.3.6.1.2.1.25.2.3.1.6.1",
		"1.3.6.1.2.1.25.2.3.1.5.1",
		"1.3.6.1.2.1.2.2.1.14.1",
		"1.3.6.1.2.1.2.2.1.20.1",
	}

	polldevice(snmp, oids)
	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		polldevice(snmp, oids)

	}

}

func polldevice(snmp *gosnmp.GoSNMP, oids []string) {
	result, err := snmp.Get(oids)
	if err != nil {
		log.Printf("get error:%v", err)
		return
	}
	for _, variable := range result.Variables {
		fmt.Printf("OID:%s|Value :%v\n", variable.Name, variable.Value)

	}

}
