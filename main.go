package main

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	"github.com/gosnmp/gosnmp"
)

func main() {
	snmp := &gosnmp.GoSNMP{
		Target:        "127.0.0.1",
		Port:          2161,
		Version:       gosnmp.Version3,
		SecurityModel: gosnmp.UserSecurityModel,
		MsgFlags:      gosnmp.NoAuthNoPriv,
		SecurityParameters: &gosnmp.UsmSecurityParameters{
			UserName: "snmpuser",
		},
		Timeout: time.Duration(2) * time.Second,
		Retries: 3,
	}

	err := snmp.Connect()
	if err != nil {
		log.Fatalf("Connect error: %v", err)
	}
	defer snmp.Conn.Close()

	db, err := openDatabase()
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	oids := []string{
		"1.3.6.1.2.1.25.3.3.1.2.1",
		"1.3.6.1.2.1.25.2.3.1.6.1",
		"1.3.6.1.2.1.25.2.3.1.5.1",
		"1.3.6.1.2.1.2.2.1.14.1",
		"1.3.6.1.2.1.2.2.1.20.1",
	}

	readingsChan := make(chan Reading)

	go snmpWorker(snmp, oids, readingsChan)
	go dbWorker(db, readingsChan)

	select {}
}

func snmpWorker(snmp *gosnmp.GoSNMP, oids []string, out chan<- Reading) {
	reading, err := polldevice(snmp, oids)
	if err == nil {
		out <- reading
	}

	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		reading, err := polldevice(snmp, oids)
		if err == nil {
			out <- reading
		}
	}
}

func dbWorker(db *sql.DB, in <-chan Reading) {
	for reading := range in {
		err := saveReading(db, reading)
		if err != nil {
			log.Printf("Save error: %v", err)
		} else {
			log.Println("Reading saved to database")
		}
	}
}

func polldevice(snmp *gosnmp.GoSNMP, oids []string) (Reading, error) {
	fmt.Println("polldevice function started")
	result, err := snmp.Get(oids)
	if err != nil {
		return Reading{}, err
	}
	reading := Reading{
		Device:      snmp.Target,
		CollectedAt: time.Now(),
	}
	for _, variable := range result.Variables {
		fmt.Printf("OID:%s|Value :%v\n", variable.Name, variable.Value)

		if variable.Name == ".1.3.6.1.2.1.25.3.3.1.2.1" {
			value := gosnmp.ToBigInt(variable.Value).Int64()
			reading.CPU = int(value)
		}
		if variable.Name == ".1.3.6.1.2.1.25.2.3.1.6.1" {
			value := gosnmp.ToBigInt(variable.Value).Int64()
			reading.MemoryUsed = int(value)
		}

		if variable.Name == ".1.3.6.1.2.1.25.2.3.1.5.1" {
			value := gosnmp.ToBigInt(variable.Value).Int64()
			reading.MemoryTotal = int(value)
		}

		if variable.Name == ".1.3.6.1.2.1.2.2.1.14.1" {
			value := gosnmp.ToBigInt(variable.Value).Int64()
			reading.InterfaceInErrors = int(value)
		}

		if variable.Name == ".1.3.6.1.2.1.2.2.1.20.1" {
			value := gosnmp.ToBigInt(variable.Value).Int64()
			reading.InterfaceOutErrors = int(value)
		}
	}
	fmt.Println("reading captured:", reading)

	return reading, nil
}
