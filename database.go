package main

import (
	"database/sql"
	"fmt"
	"time"

	_ "modernc.org/sqlite"
)

type Reading struct {
	Device             string
	CollectedAt        time.Time
	CPU                int
	MemoryUsed         int
	MemoryTotal        int
	InterfaceInErrors  int
	InterfaceOutErrors int
}

func openDatabase() (*sql.DB, error) {
	db, err := sql.Open("sqlite", "network_monitor.db")
	if err != nil {
		return nil, fmt.Errorf("failed to open database file: %w", err)
	}

	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("database opened but not reachable: %w", err)
	}

	fmt.Println("Database opened successfully")

	createTableSQL := `
	CREATE TABLE IF NOT EXISTS readings (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		device TEXT NOT NULL,
		collected_at TEXT NOT NULL,
		cpu INTEGER NOT NULL,
		memory_used INTEGER NOT NULL,
		memory_total INTEGER NOT NULL,
		interface_in_errors INTEGER NOT NULL,
		interface_out_errors INTEGER NOT NULL
	);`

	if _, err := db.Exec(createTableSQL); err != nil {
		return nil, fmt.Errorf("failed to create readings table: %w", err)
	}
	fmt.Println("Table ready")

	return db, nil
}

func saveReading(db *sql.DB, r Reading) error {
	if db == nil {
		return fmt.Errorf("saveReading called with nil database connection")
	}

	if r.Device == "" {
		return fmt.Errorf("saveReading called with empty device field")
	}

	insertSQL := `
	INSERT INTO readings (device, collected_at, cpu, memory_used, memory_total, interface_in_errors, interface_out_errors)
	VALUES (?, ?, ?, ?, ?, ?, ?);`

	_, err := db.Exec(insertSQL,
		r.Device,
		r.CollectedAt.Format(time.RFC3339),
		r.CPU,
		r.MemoryUsed,
		r.MemoryTotal,
		r.InterfaceInErrors,
		r.InterfaceOutErrors,
	)
	if err != nil {
		return fmt.Errorf("failed to insert reading for device %s: %w", r.Device, err)
	}

	return nil
}
