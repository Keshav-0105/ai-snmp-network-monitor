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

	oids := []string{"1.3.6.1.2.1.25.3.3.1.2.1"}

	result, err := snmp.Get(oids)
	if err != nil {
		log.Fatalf("Get error: %v", err)
	}

	for _, variable := range result.Variables {
		fmt.Printf("OID: %s\n", variable.Name)
		fmt.Printf("CPU Load: %v\n", variable.Value)
	}
}
