package main

import (

	"fmt"
	"log"
	"os"
	"time"

	"github.com/gosnmp/gosnmp"
)

func main() {
	readingsChan := make(chan Reading)

	startPort := 2161
	endPort := 2200

	for port := startPort; port <= endPort; port++ {
		go snmpWorker(port, readingsChan)
	}

	go dbWorker(readingsChan)

	select {}
}

func snmpWorker(port int, out chan<- Reading) {
	target := os.Getenv("SNMP_TARGET")
	if target == "" {
		target = "127.0.0.1"
	}

	attemptConnection := func() {
		snmp := &gosnmp.GoSNMP{
			Target:        target,
			Port:          uint16(port),
			Version:       gosnmp.Version3,
			SecurityModel: gosnmp.UserSecurityModel,
			MsgFlags:      gosnmp.NoAuthNoPriv,
			SecurityParameters: &gosnmp.UsmSecurityParameters{
				UserName: "snmpuser",
			},
			ContextName: "public",
			Timeout:     time.Duration(2) * time.Second,
			Retries:     3,
		}

		if err := snmp.Connect(); err != nil {
			return
		}
		defer func() {
			if err := snmp.Conn.Close(); err != nil {
				log.Printf("Warning: failed to close SNMP connection on port %d: %v", port, err)
			}
		}()

		oids := []string{
			"1.3.6.1.2.1.25.3.3.1.2.1",
			"1.3.6.1.2.1.25.2.3.1.6.1",
			"1.3.6.1.2.1.25.2.3.1.5.1",
			"1.3.6.1.2.1.2.2.1.14.1",
			"1.3.6.1.2.1.2.2.1.20.1",
		}

		reading, err := polldevice(snmp, oids)
		if err != nil {
			log.Printf("Poll error on port %d: %v", port, err)
			return
		}

		log.Printf("Device found and polled on port %d", port)
		out <- reading
	}

	attemptConnection()

	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		attemptConnection()
	}
}

func dbWorker(in <-chan Reading) {
	db, err := openDatabase()
	if err != nil {
		log.Fatalf("Cannot start dbWorker: %v", err)
	}
	defer db.Close()

	for reading := range in {
		if err := saveReading(db, reading); err != nil {
			log.Printf("Save error for device %s: %v", reading.Device, err)
			continue
		}
		log.Printf("Reading saved to database (device: %s, CPU: %d)", reading.Device, reading.CPU)
	}
}

func polldevice(snmp *gosnmp.GoSNMP, oids []string) (Reading, error) {
	if snmp == nil {
		return Reading{}, fmt.Errorf("polldevice called with nil SNMP connection")
	}
	if len(oids) == 0 {
		return Reading{}, fmt.Errorf("polldevice called with empty OID list")
	}

	result, err := snmp.Get(oids)
	if err != nil {
		return Reading{}, fmt.Errorf("SNMP Get failed for target %s: %w", snmp.Target, err)
	}

	reading := Reading{
		Device:      snmp.Target,
		CollectedAt: time.Now(),
	}

	for _, variable := range result.Variables {
		switch variable.Name {
		case ".1.3.6.1.2.1.25.3.3.1.2.1":
			reading.CPU = int(gosnmp.ToBigInt(variable.Value).Int64())
		case ".1.3.6.1.2.1.25.2.3.1.6.1":
			reading.MemoryUsed = int(gosnmp.ToBigInt(variable.Value).Int64())
		case ".1.3.6.1.2.1.25.2.3.1.5.1":
			reading.MemoryTotal = int(gosnmp.ToBigInt(variable.Value).Int64())
		case ".1.3.6.1.2.1.2.2.1.14.1":
			reading.InterfaceInErrors = int(gosnmp.ToBigInt(variable.Value).Int64())
		case ".1.3.6.1.2.1.2.2.1.20.1":
			reading.InterfaceOutErrors = int(gosnmp.ToBigInt(variable.Value).Int64())
		}
	}

	if reading.MemoryTotal == 0 {
		return reading, fmt.Errorf("received reading with zero MemoryTotal for device %s, data may be invalid", snmp.Target)
	}

	return reading, nil
}

