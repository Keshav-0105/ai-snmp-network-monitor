package main

import (
	"fmt"
	"log"
	"os"
	"time"

	"github.com/gosnmp/gosnmp"
)

// main starts one goroutine per SNMP port in the range 2161-2200 (each
// representing a simulated device), plus one goroutine that writes every
// collected reading to the database. All communication happens through
// readingsChan so pollers never block on database writes and vice versa.
func main() {
	readingsChan := make(chan Reading)

	startPort := 2161
	endPort := 2200

	// Launch a dedicated poller goroutine for every device port.
	for port := startPort; port <= endPort; port++ {
		go snmpWorker(port, readingsChan)
	}

	// Launch the single goroutine responsible for persisting readings.
	go dbWorker(readingsChan)

	// Block forever — all real work happens in the goroutines above.
	select {}
}

// snmpWorker repeatedly polls a single device (identified by port) over
// SNMPv3, once immediately and then every 60 seconds. Successful readings
// are sent to out; failed polls are logged and simply skipped rather than
// crashing the worker, so a temporarily unreachable device doesn't bring
// down monitoring for the rest.
func snmpWorker(port int, out chan<- Reading) {
	target := os.Getenv("SNMP_TARGET")
	if target == "" {
		target = "127.0.0.1" // default to localhost for local simulator use
	}

	// attemptConnection performs one full connect -> poll -> send cycle.
	// Defined as a closure so it can be reused for both the initial poll
	// and every subsequent tick without duplicating this setup logic.
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

		// If the device isn't reachable, silently return — this port will
		// simply be retried on the next tick rather than terminating the
		// whole worker.
		if err := snmp.Connect(); err != nil {
			return
		}
		defer func() {
			if err := snmp.Conn.Close(); err != nil {
				log.Printf("Warning: failed to close SNMP connection on port %d: %v", port, err)
			}
		}()

		// The 5 OIDs this project cares about: CPU load, memory used,
		// memory total, interface inbound errors, interface outbound errors.
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

	// Poll once immediately on startup, rather than waiting a full 60s
	// for the first reading.
	attemptConnection()

	// Then poll on a fixed 60-second interval for the lifetime of the program.
	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		attemptConnection()
	}
}

// dbWorker owns the single database connection for the whole program and
// consumes readings from in as they arrive, writing each one to SQLite.
// Running as the only writer avoids concurrent-write issues with SQLite.
func dbWorker(in <-chan Reading) {
	db, err := openDatabase()
	if err != nil {
		log.Fatalf("Cannot start dbWorker: %v", err)
	}
	defer db.Close()

	for reading := range in {
		if err := saveReading(db, reading); err != nil {
			log.Printf("Save error for device %s: %v", reading.Device, err)
			continue // one bad write shouldn't stop the worker from processing the rest
		}
		log.Printf("Reading saved to database (device: %s, CPU: %d)", reading.Device, reading.CPU)
	}
}

// polldevice sends a single SNMP GET for all given OIDs against an already-
// connected snmp client, and maps the returned values onto a Reading struct
// by matching each OID string to the field it represents.
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

	// Match each returned variable back to the field it represents by OID.
	// gosnmp returns OIDs prefixed with a leading dot, hence ".1.3.6..." below.
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

	// A MemoryTotal of 0 almost always means the device returned garbage
	// or unsupported OIDs rather than real data, so treat it as an error
	// instead of silently storing a bad reading.
	if reading.MemoryTotal == 0 {
		return reading, fmt.Errorf("received reading with zero MemoryTotal for device %s, data may be invalid", snmp.Target)
	}

	return reading, nil
}
