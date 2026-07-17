/// Full mTLS emulator — generates certs at runtime, requests client cert, logs everything
/// Build: GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -ldflags="-s -w"

package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"flag"
	"fmt"
	"io"
	"log"
	"math/big"
	"net"
	"os"
	"strings"
	"time"
)

func genCert(commonName string, isCA bool, caCert *x509.Certificate, caKey *rsa.PrivateKey) ([]byte, []byte) {
	key, _ := rsa.GenerateKey(rand.Reader, 2048)
	serial, _ := rand.Int(rand.Reader, new(big.Int).Lsh(big.NewInt(1), 128))
	tmpl := &x509.Certificate{
		SerialNumber: serial,
		Subject:      pkix.Name{CommonName: commonName, Organization: []string{"VIDAA Emulator"}},
		NotBefore:    time.Now().Add(-1 * time.Hour),
		NotAfter:     time.Now().Add(365 * 24 * time.Hour),
		KeyUsage:     x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment,
		ExtKeyUsage:  []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth, x509.ExtKeyUsageClientAuth},
		IPAddresses:  []net.IP{net.ParseIP("127.0.0.1"), net.ParseIP("0.0.0.0")},
		DNSNames:     []string{"localhost", "tv.emulator.local"},
	}
	if isCA {
		tmpl.IsCA = true
		tmpl.KeyUsage |= x509.KeyUsageCertSign
		tmpl.BasicConstraintsValid = true
	}
	if caCert == nil {
		caCert = tmpl
		caKey = key
	}
	certDER, _ := x509.CreateCertificate(rand.Reader, tmpl, caCert, &key.PublicKey, caKey)
	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: certDER})
	keyPEM := pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(key)})
	return certPEM, keyPEM
}

func encLen(l int) []byte {
	e := []byte{}
	for { d := byte(l % 128); l /= 128; if l > 0 { d |= 0x80 }; e = append(e, d); if l == 0 { break } }
	return e
}
func decLen(data []byte, off int) (int, int) {
	m, v, u := 1, 0, 0
	for off+u < len(data) { d := data[off+u]; u++; v += int(d&127) * m; if d&128 == 0 { return v, u }; m *= 128 }
	return 0, 0
}
func rdStr(data []byte, off int) (string, int) {
	if off+2 > len(data) { return "", off }
	l := int(data[off])<<8 | int(data[off+1]); off += 2
	if off+l > len(data) { return "", off }
	return string(data[off : off+l]), off + l
}
func wrStr(s string) []byte { d := []byte(s); return append([]byte{byte(len(d)>>8), byte(len(d)&0xFF)}, d...) }

func handle(conn *tls.Conn) {
	defer conn.Close()
	addr := conn.RemoteAddr().String()

	// Check client cert CN (mTLS verification)
	state := conn.ConnectionState()
	reject := false
	if len(state.PeerCertificates) > 0 {
		cert := state.PeerCertificates[0]
		log.Printf("[%s] mTLS CLIENT CERT: CN='%s' issuer='%s' org=%v",
			addr, cert.Subject.CommonName, cert.Issuer.CommonName, cert.Subject.Organization)
		if cert.Subject.CommonName != "VidaaAppAndroidV01" {
			log.Printf("[%s] REJECTED: wrong CN '%s', expected 'VidaaAppAndroidV01'", addr, cert.Subject.CommonName)
			reject = true
		}
	} else {
		log.Printf("[%s] REJECTED: no client certificate presented", addr)
		reject = true
	}
	if reject {
		conn.Close()
		return
	}

	// Send state broadcast
	topic := "/remoteapp/mobile/broadcast/ui_service/state"
	body := `{"statetype":"tvon","source":"HDMI1"}`
	msg := wrStr(topic)
	msg = append(msg, []byte(body)...)
	hdr := []byte{0x30}
	hdr = append(hdr, encLen(len(msg))...)
	conn.Write(append(hdr, msg...))

	buf := make([]byte, 4096)
	for {
		conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		n, err := conn.Read(buf)
		if err != nil { if err != io.EOF { log.Printf("[%s] Read err: %v", addr, err) }; return }
		if n < 2 { continue }

		ptype := (buf[0] & 0xF0) >> 4
		plen, hl := decLen(buf, 1)
		if plen == 0 && hl == 0 { continue }
		if n < 1+hl+plen { continue }

		switch ptype {
		case 1: // CONNECT
			conn.Write([]byte{0x20, 0x02, 0x00, 0x00})
			payload := buf[1+hl : n]
			off := 0
			proto, off := rdStr(payload, off)
			if off >= len(payload) { continue }
			ver := payload[off]; off++
			if off >= len(payload) { continue }
			flags := payload[off]; off++
			off += 2 // keepalive
			cid, off := rdStr(payload, off)
			user := ""
			if flags&0x80 != 0 {
				user, off = rdStr(payload, off)
			}
			cidStr := cid
			if len(cidStr) > 60 { cidStr = cidStr[:60] }
			userStr := user
			if len(userStr) > 30 { userStr = userStr[:30] }
			log.Printf("[%s] MQTT CONNECT: proto=%s ver=%d cid=%s user=%s", addr, proto, ver, cidStr, userStr)
			log.Printf("[%s] CONNACK sent (accepted)", addr)

		case 3: // PUBLISH
			payload := buf[1+hl : n]
			topic, _ := rdStr(payload, 0)
			body := strings.TrimSpace(string(payload[len(topic)+2:]))  // +2 for length prefix
			log.Printf("[%s] PUBLISH: topic=%s", addr, topic)
			bodyStr := body
			if len(bodyStr) > 60 { bodyStr = bodyStr[:60] }
			log.Printf("[%s]          data=%s", addr, bodyStr)

		case 8: // SUBSCRIBE
			payload := buf[1+hl : n]
			pid := (uint16(payload[0])<<8 | uint16(payload[1]))
			conn.Write([]byte{0x90, 0x03, byte(pid>>8), byte(pid&0xFF), 0})

		case 12: // PINGREQ
			conn.Write([]byte{0xD0, 0x00})
		}
	}
}

func main() {
	port := flag.Int("port", 36669, "Listen port")
	flag.Parse()

	log.SetFlags(log.LstdFlags | log.Lmicroseconds)

	// Generate CA
	caCertPEM, caKeyPEM := genCert("VIDAA Emulator CA", true, nil, nil)
	caCertBlock, _ := pem.Decode(caCertPEM)
	caCert, _ := x509.ParseCertificate(caCertBlock.Bytes)
	caKeyBlock, _ := pem.Decode(caKeyPEM)
	caKey, _ := x509.ParsePKCS1PrivateKey(caKeyBlock.Bytes)

	// Generate server cert signed by CA
	srvCertPEM, srvKeyPEM := genCert("tv.emulator.local", false, caCert, caKey)

	cert, _ := tls.X509KeyPair(srvCertPEM, srvKeyPEM)
	caPool := x509.NewCertPool()
	caPool.AppendCertsFromPEM(caCertPEM)

	// mTLS: require client cert, check CN after handshake
	tlsCfg := &tls.Config{
		Certificates: []tls.Certificate{cert},
		ClientAuth:   tls.RequestClientCert, // Request cert, check CN manually
		ClientCAs:    caPool,
		MinVersion:   tls.VersionTLS12,
	}

	addr := fmt.Sprintf("0.0.0.0:%d", *port)
	l, _ := tls.Listen("tcp", addr, tlsCfg)
	defer l.Close()

	log.Printf("===== VIDAA TV EMULATOR (mTLS) =====")
	log.Printf("Listening on %s", addr)
	log.Printf("Server cert: CN=%s", cert.Leaf.Subject.CommonName)
	log.Printf("CA cert:     CN=%s", caCert.Subject.CommonName)
	log.Printf("Mode:        RequestClientCert (logs all certs)")
	log.Printf("=====================================")

	for {
		conn, err := l.Accept()
		if err != nil { log.Printf("Accept: %v", err); continue }
		log.Printf(">>> New TLS connection from %s", conn.RemoteAddr())
		go handle(conn.(*tls.Conn))
	}
	os.Exit(0)
}
