package main

import (
	"crypto/tls"
	"fmt"
	"os"
)

func main() {
	cert, err := tls.LoadX509KeyPair("evil_cert.pem", "evil_key.pem")
	if err != nil {
		fmt.Println("ERROR:", err)
		os.Exit(1)
	}
	fmt.Println("OK, CN=", cert.Leaf)
}
