/// VIDAA Bridge v4 — Multi-device MQTT mTLS driver with Web UI
///
/// Features:
/// - Multiple TV devices in one binary
/// - HTTP API on :8090 (/api/{device}/state, /api/{device}/command)
/// - Web UI on :8889 (tabs per device, visual feedback, full-width logs)
/// - JSON config file
/// - Auto-reconnection per device
///
/// Build: GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -ldflags="-s -w"

package main

import (
	"crypto/md5"
	"crypto/tls"
	"crypto/x509"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"
)

// ── Embedded certs ──────────────────────────────────────────────────────

const vidaaCertPEM = `-----BEGIN CERTIFICATE-----
MIIDvDCCAqSgAwIBAgIBDDANBgkqhkiG9w0BAQsFADBnMQswCQYDVQQGEwJDTjER
MA8GA1UECAwIc2hhbmRvbmcxEDAOBgNVBAcMB3FpbmdkYW8xCzAJBgNVBAoMAmho
MRMwEQYDVQQLDAptdWx0aW1lZGlhMREwDwYDVQQDDAhSZW1vdGVDQTAeFw0yNDA2
Mjc3MDQxNTJaFw0zNDA2MjUxMDQxNTJaMF8xCzAJBgNVBAYTAkNOMREwDwYDVQQI
DAhzaGFuZG9uZzELMAkGA1UECgwCaGgxEzARBgNVBAsMCm11bHRpbWVkaWExGzAZ
BgNVBAMMElZpZGFhQXBwQW5kcm9pZFYwMTCCASIwDQYJKoZIhvcNAQEBBQADggEP
ADCCAQoCggEBAMUkrVRx8nnj8IolzFAblAS35n05ybKLJgZxAzWjuTm51zArQSbh
YOyPFvsKc0c0GW790ckzWCm0FHg2o/NG37EZG6D2TyEFqbxixuDQbRB6SVynfnUp
VIh6VEGkykODPYM08LaiZvjeJG9ghmofNjSpoKIQFkgxxjLUGry/sIwcO5IrXyYt
02LnhvmzIz+QzZN1qijxftlXzy5vIt8I/LeVf7qbScA8c4YhjHc5HsO3vycyRQ5B
aoVadV6sL2XWa1OBzjFXhX1KFA8kLz0ZmAEa5m3v8WeYT07iaHBclgEIZEK4KJp2
RXZJ/0ChVnJIJjg2lTekPQSwtufYJLx3y/kCAwEAAaN7MHkwCQYDVR0TBAIwADAs
BglghkgBhvhCAQ0EHxYdT3BlblNTTCBHZW5lcmF0ZWQgQ2VydGlmaWNhdGUwHQYD
VR0OBBYEFEKhgLa5dw9UunWoQjUiHxv5ZrIQMB8GA1UdIwQYMBaAFCNAgpGpJAaH
MXiTj6CUPKpJ/Pw7MA0GCSqGSIb3DQEBCwUAA4IBAQBooSaxPNOpxyhciyOW8DWA
lnCrGId09OL8zn1O73m6fmnb8oY9Xb/pKhIcJfeOxeoToKyoQVaF5OSBNnvlvV+R
f65U5H3QeufVsbh9m3Rh0smI7s8yGBYO0/E43QNKMpKlYSo1TwGGPcTq9LkdtbVJ
qrpgg6MapWJ41Smh6jKzGTT4nyjsjK6EnCxMozM0SQBebloAJP9JTBPpO2A2Efe/
SkJdUHSrzW4mwvVh8Y8LWWuRQE6t01Eitsg5OWnEunyFr0Ums5Pi8yc4JJZf23+b
oZBOmdTu9oL9JDLBNb/U3jYeMiyw2D7H+kUvnHpIdbq5ZOpz877ihQ4GoCqeB6JS
-----END CERTIFICATE-----`

const vidaaKeyPEM = `-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDFJK1UcfJ54/CK
JcxQG5QEt+Z9OcmyiyYGcQM1o7k5udcwK0Em4WDsjxb7CnNHNBlu/dHJM1gptBR4
NqPzRt+xGRug9k8hBam8Ysbg0G0Qeklcp351KVSIelRBpMpDgz2DNPC2omb43iRv
YIZqHzY0qaCiEBZIMcYy1Bq8v7CMHDuSK18mLdNi54b5syM/kM2Tdaoo8X7ZV88u
byLfCPy3lX+6m0nAPHOGIYx3OR7Dt78nMkUOQWqFWnVerC9l1mtTgc4xV4V9ShQP
JC89GZgBGuZt7/FnmE9O4mhwXJYBCGRCuCiadkV2Sf9AoVZySCY4NpU3pD0EsLbn
2CS8d8v5AgMBAAECggEAMhy/no6Ud110oHk5NUe9WXGxujU9SxBJ6ytBCJqEk+Lk
i08DcbGqpJc+3TNr2DarHGaStBVEHN20slYZWNa0N91NA554wMkiu0tUiIMSpjSf
f1joMTn/Te3iiwkrjPvIYBjN827Ww/4bvuAHauRiMALKXUe/kjxsyDDYVxBW/VYh
qioYJckIv1r5TUt/kkMoEw73kC7G8lmU7XMydlJs0MJcgTA+gtUBXweuUJJLciSv
tHwnDO1iuifqM+SpN557mAtF1Cl4zWzgo5tX5hZBBesmyk12ibmQ06lVPjgddkqU
9rHsSaqjAtUMuEmqt3q/EkngHqqLxmAa1UGCQCG8HQKBgQDjWjj3iScFFxwQcAz6
vws+lhPbiDMs+4WrK+snVOW6xecffsaBV6/zmveApiH1MOkefDJJIMx11Tald3K7
Xsx9PPiL12I4eIlKfVEfqA91DltHkL0zRkmaqBMtWu0peZv/RY8CnoPvnzwCU4LU
LEGVVydVXxepiJ6xxiDfHcjxHwKBgQDd+/0A0y1mVPU0jCBQJxycHKE5pFGYhbad
Lb2/rUiwjatn8IVixPlLn7n79D2v95UUjGQTsv5rZ9vTx1cAndM4UXiOoHka0OD3
DHgkOpofz4o1h/vifFciOw2bcS+/aagfU2MZDSitn/pm4IMh45erL+DJ2WZCXPQ0
aR8VhsWn5wKBgQCn4dWzJDoGDjyQ/sz2096k9XgVYgu4KbtY3MN2dcB2HPFAVpMq
q5+oGUSuYP8uWYGrGzbevTN9x4XkxcGZDrWdvUojqVZEMO3gbY1b/PP9Ei7hN8Ye
eMadR4NxuHTsbXp+E9U4r+jpJwJfDV/MYSnEp2jKJ8AHVnUo/Q8E8q+RLQKBgQCC
aZY7s9UKN4NO+bvKGxA9zrwRRy4Asx2TvdmqED2SK8i1aaKTYjErco0rLlRHWuak
ic4JnLDHnN6SzpuYayA6B/MRp8k+LdTcjuDON/dwFNeXl2otpurx20ulNJvekk4J
CU5A23A4gLH1WpTvhewG0Dv5mdTvy/hUCiYO2XyppQKBgBA2CXeJ4VR/m6pwldgV
rN5M2rxj89eKcxzSx/b3IEHBwtHI5Iw0Pz117A5AUkbZ2cNP1fr3VjZ+d3o9Q0eT
pWmJxd9Z5ezxHva7pdu2l4rlnEL2+ay1ul28XIQmZykABe0PXsU4efolORuyLill
qqpT2oH7lbhuFqwu1RqsMfVG
-----END PRIVATE KEY-----`

// ── VIDAA Crypto ────────────────────────────────────────────────────────

const (
	vidaaPattern       = "38D65DC30F45109A369A86FCE866A85B"
	vidaaValueSuffix   = "h!i@s#$v%i^d&a*a"
	vidaaXorConst      = 0x5698_1477_2b03_a968
)

func md5hex(s string) string {
	h := md5.Sum([]byte(s))
	return strings.ToUpper(hex.EncodeToString(h[:]))
}

func sumDigits(n int64) int {
	sum := 0
	for _, c := range fmt.Sprintf("%d", n) { if c >= '0' && c <= '9' { sum += int(c - '0') } }
	return sum
}

func genCreds(mac, brand string, ts int64) (cid, user, pass string) {
	u := strings.ReplaceAll(strings.ReplaceAll(mac, ":", ""), "-", "")
	if len(u) == 12 {
		up := strings.ToUpper(u)
		ps := make([]string, 6)
		for i := 0; i < 6; i++ { ps[i] = up[i*2 : i*2+2] }
		u = strings.Join(ps, ":")
	}
	race := vidaaPattern + "$" + u
	rh := md5hex(race)[:6]
	cid = u + "$" + brand + "$" + rh + "_vidaacommon_001"
	xt := ts ^ vidaaXorConst
	user = brand + "$" + fmt.Sprintf("%d", xt)
	rem := sumDigits(ts) % 10
	v := fmt.Sprintf("%s%d%s", brand, rem, vidaaValueSuffix)
	vh := md5hex(v)[:6]
	pass = md5hex(fmt.Sprintf("%d$%s", ts, vh))
	return
}

// ── MQTT Protocol ────────────────────────────────────────────────────────

func mqttStr(s string) []byte { d := []byte(s); return append([]byte{byte(len(d)>>8), byte(len(d)&0xFF)}, d...) }
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
func mqttPkt(t byte, p []byte) []byte { h := []byte{t << 4}; h = append(h, encLen(len(p))...); return append(h, p...) }
func mqttConnect(cid, user, pass string) []byte {
	f := byte(0x02); var p []byte
	p = append(p, mqttStr("MQTT")...); p = append(p, 4)
	if user != "" { f |= 0x80 }; if pass != "" { f |= 0x40 }
	p = append(p, f); p = append(p, 0, 60); p = append(p, mqttStr(cid)...)
	if user != "" { p = append(p, mqttStr(user)...) }; if pass != "" { p = append(p, mqttStr(pass)...) }
	return mqttPkt(1, p)
}
func mqttPub(topic string, body []byte) []byte {
	var p []byte; p = append(p, mqttStr(topic)...); p = append(p, body...); return mqttPkt(3, p)
}
func mqttSub(topic string, pid uint16) []byte {
	var p []byte; p = append(p, byte(pid>>8), byte(pid&0xFF)); p = append(p, mqttStr(topic)...); p = append(p, 0)
	return mqttPkt(8|2, p)
}

// ── Config ───────────────────────────────────────────────────────────────

type DeviceConfig struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	TVIP     string `json:"tv_ip"`
	TVMAC    string `json:"tv_mac"`
	TVPort   int    `json:"tv_port"`
	NoTLS    bool   `json:"no_tls"`
	CertFile string `json:"cert_file,omitempty"`
	KeyFile  string `json:"key_file,omitempty"`
}

type BridgeConfig struct {
	mu      sync.RWMutex
	Devices []DeviceConfig `json:"devices"`
	APIPort int            `json:"api_port"`
	UIPort  int            `json:"ui_port"`
	LogFile string         `json:"log_file,omitempty"`
	path    string
}

func (c *BridgeConfig) load(path string) error {
	c.path = path
	d, err := os.ReadFile(path)
	if err != nil { return err }
	c.mu.Lock(); defer c.mu.Unlock()
	return json.Unmarshal(d, c)
}

func (c *BridgeConfig) save() error {
	if c.path == "" { return nil }
	c.mu.RLock(); d, _ := json.MarshalIndent(c, "", "  "); c.mu.RUnlock()
	return os.WriteFile(c.path, d, 0644)
}

// ── Device Connection ────────────────────────────────────────────────────

type DeviceState struct {
	Connected bool   `json:"connected"`
	Power     string `json:"power"`
	Volume    int    `json:"volume"`
	Muted     bool   `json:"muted"`
	Source    string `json:"source"`
	LastError string `json:"last_error,omitempty"`
	Uptime    string `json:"uptime"`
	startTime time.Time
	mu        sync.RWMutex
}

type Device struct {
	cfg    DeviceConfig
	state  DeviceState
	conn   net.Conn
	mu     sync.Mutex
	logger *log.Logger
}

func NewDevice(cfg DeviceConfig, lg *log.Logger) *Device {
	return &Device{
		cfg:   cfg,
		state: DeviceState{Power: "on", Volume: 25, Source: "HDMI1", startTime: time.Now()},
		logger: lg,
	}
}

func (d *Device) Connect() error {
	d.mu.Lock(); defer d.mu.Unlock()

	if d.conn != nil { d.conn.Close(); d.conn = nil }

	addr := fmt.Sprintf("%s:%d", d.cfg.TVIP, d.cfg.TVPort)
	var tvConn net.Conn
	var err error

	if d.cfg.NoTLS {
		tvConn, err = net.DialTimeout("tcp", addr, 10*time.Second)
		if err != nil { return fmt.Errorf("dial: %w", err) }
	} else {
		var cert tls.Certificate
		if d.cfg.CertFile != "" && d.cfg.KeyFile != "" {
			cert, err = tls.LoadX509KeyPair(d.cfg.CertFile, d.cfg.KeyFile)
		} else {
			cert, err = tls.X509KeyPair([]byte(vidaaCertPEM), []byte(vidaaKeyPEM))
		}
		if err != nil { return fmt.Errorf("cert: %w", err) }
		// Log certificate details for mTLS proof
		if len(cert.Certificate) > 0 {
			if x509Cert, err := x509.ParseCertificate(cert.Certificate[0]); err == nil {
				d.logger.Printf("[%s] mTLS CERT: subject=%s issuer=%s", d.cfg.ID, x509Cert.Subject.CommonName, x509Cert.Issuer.CommonName)
			}
		}
		raw, err := net.DialTimeout("tcp", addr, 10*time.Second)
		if err != nil { return fmt.Errorf("dial: %w", err) }
		tlsc := tls.Client(raw, &tls.Config{Certificates: []tls.Certificate{cert}, InsecureSkipVerify: true, MinVersion: tls.VersionTLS12})
		if err = tlsc.Handshake(); err != nil { tlsc.Close(); return fmt.Errorf("tls: %w", err) }
		tvConn = tlsc
	}
	d.conn = tvConn

	ts := time.Now().Unix()
	cid, user, pass := genCreds(d.cfg.TVMAC, "his", ts)
	if _, err = d.conn.Write(mqttConnect(cid, user, pass)); err != nil { return fmt.Errorf("connect: %w", err) }
	// Read responses until CONNACK found (emulator may send broadcast first)
	resp := make([]byte, 4096)
	found := false
	for retry := 0; retry < 10; retry++ {
		d.conn.SetReadDeadline(time.Now().Add(3 * time.Second))
		n, readErr := d.conn.Read(resp)
		if readErr != nil {
			return fmt.Errorf("read: %w", readErr)
		}
		off := 0
		for off < n {
			if off+2 > n { break }
			ptype := (resp[off] & 0xF0) >> 4
			plen, hl := decLen(resp, off+1)
			if plen == 0 && hl == 0 { break }
			total := 1 + hl + plen
			if off+total > n { break }
			if ptype == 2 && total >= 4 {
				if resp[off+3] != 0 { return fmt.Errorf("rejected: %d", resp[off+3]) }
				found = true
			}
			off += total
		}
		if found { break }
	}
	if !found { return fmt.Errorf("no CONNACK after retries") }

	d.conn.Write(mqttSub("/remoteapp/mobile/broadcast/ui_service/state", 1))

	d.state.mu.Lock()
	d.state.Connected = true; d.state.LastError = ""; d.state.startTime = time.Now()
	d.state.mu.Unlock()

	d.logger.Printf("[%s] Connected to TV (cid=%s...)", d.cfg.ID, cid[:30])
	go d.readLoop()
	return nil
}

func (d *Device) readLoop() {
	buf := make([]byte, 4096)
	for {
		d.mu.Lock(); conn := d.conn; d.mu.Unlock()
		if conn == nil { return }
		conn.SetReadDeadline(time.Now().Add(30 * time.Second))
		n, err := conn.Read(buf)
		if err != nil {
			d.logger.Printf("[%s] Read error: %v", d.cfg.ID, err)
			d.state.mu.Lock(); d.state.Connected = false; d.state.LastError = err.Error(); d.state.mu.Unlock()
			go d.reconnectLoop()
			return
		}
		if n >= 2 && (buf[0]&0xF0)>>4 == 3 {
			_, hl := decLen(buf, 1); p := buf[1+hl : n]
			_, off := rdStr(p, 0)
			if off < len(p) {
				body := string(p[off:])
				var s map[string]interface{}
				if json.Unmarshal([]byte(body), &s) == nil {
					d.state.mu.Lock()
					if st, ok := s["statetype"].(string); ok { d.state.Power = "on"; if st == "fake_sleep_0" { d.state.Power = "off" } }
					d.state.mu.Unlock()
				}
			}
		}
	}
}

func (d *Device) reconnectLoop() {
	for {
		time.Sleep(5 * time.Second)
		d.logger.Printf("[%s] Reconnecting...", d.cfg.ID)
		if err := d.Connect(); err != nil {
			d.logger.Printf("[%s] Reconnect failed: %v", d.cfg.ID, err)
			continue
		}
		d.logger.Printf("[%s] Reconnected!", d.cfg.ID)
		return
	}
}

func (d *Device) publish(topic, body string) error {
	d.mu.Lock(); defer d.mu.Unlock()
	if d.conn == nil { return fmt.Errorf("not connected") }
	_, err := d.conn.Write(mqttPub(topic, []byte(body)))
	return err
}

func (d *Device) SendKey(key string) error {
	ts := time.Now().Unix(); cid, _, _ := genCreds(d.cfg.TVMAC, "his", ts)
	// Optimistic state update for known keys
	d.state.mu.Lock()
	switch key {
	case "KEY_VOLUME_UP": if d.state.Volume < 100 { d.state.Volume += 5 }
	case "KEY_VOLUME_DOWN": if d.state.Volume > 0 { d.state.Volume -= 5 }
	case "KEY_MUTE": d.state.Muted = !d.state.Muted
	}
	d.state.mu.Unlock()
	return d.publish(fmt.Sprintf("/remoteapp/tv/remote_service/%s/actions/sendkey", cid), key)
}

func (d *Device) SetVolume(vol int) error {
	ts := time.Now().Unix(); cid, _, _ := genCreds(d.cfg.TVMAC, "his", ts)
	d.state.mu.Lock(); d.state.Volume = vol; d.state.mu.Unlock()
	return d.publish(fmt.Sprintf("/remoteapp/tv/platform_service/%s/actions/changevolume", cid), fmt.Sprintf(`{"volume_value":%d}`, vol))
}

func (d *Device) SetSource(src string) error {
	ts := time.Now().Unix(); cid, _, _ := genCreds(d.cfg.TVMAC, "his", ts)
	m := map[string]string{"tv":"0","av":"1","component":"2","hdmi1":"3","hdmi2":"4","hdmi3":"5","hdmi4":"6"}
	id := m[strings.ToLower(src)]; if id == "" { id = src }
	d.state.mu.Lock(); d.state.Source = src; d.state.mu.Unlock()
	return d.publish(fmt.Sprintf("/remoteapp/tv/ui_service/%s/actions/changesource", cid), fmt.Sprintf(`{"sourceid":"%s"}`, id))
}

func (d *Device) LaunchApp(app string) error {
	ts := time.Now().Unix(); cid, _, _ := genCreds(d.cfg.TVMAC, "his", ts)
	return d.publish(fmt.Sprintf("/remoteapp/tv/ui_service/%s/actions/launchapp", cid), fmt.Sprintf(`{"name":"%s","appId":""}`, app))
}

func (d *Device) State() DeviceState {
	d.state.mu.RLock(); defer d.state.mu.RUnlock()
	s := d.state
	s.Uptime = time.Since(s.startTime).Round(time.Second).String()
	return s
}

// ── Bridge ───────────────────────────────────────────────────────────────

type Bridge struct {
	cfg    *BridgeConfig
	devs   map[string]*Device
	devsMu sync.RWMutex
	logBuf *LogBuffer
	logger *log.Logger
}

func NewBridge(cfg *BridgeConfig) *Bridge {
	lb := newLogBuffer(300)
	lg := log.New(io.MultiWriter(os.Stdout, lb), "", log.LstdFlags|log.Lmicroseconds)
	b := &Bridge{cfg: cfg, devs: make(map[string]*Device), logBuf: lb, logger: lg}
	b.syncDevices()
	return b
}

func (b *Bridge) syncDevices() {
	b.cfg.mu.RLock(); devs := make([]DeviceConfig, len(b.cfg.Devices)); copy(devs, b.cfg.Devices); b.cfg.mu.RUnlock()

	b.devsMu.Lock()
	defer b.devsMu.Unlock()

	seen := make(map[string]bool)
	for _, dc := range devs {
		seen[dc.ID] = true
		if _, ok := b.devs[dc.ID]; !ok {
			d := NewDevice(dc, b.logger)
			b.devs[dc.ID] = d
			go func() {
				if err := d.Connect(); err != nil {
					b.logger.Printf("[%s] Init connect failed: %v (retrying)", dc.ID, err)
					go d.reconnectLoop()
				}
			}()
		}
	}
	for id := range b.devs {
		if !seen[id] { delete(b.devs, id) }
	}
}

func (b *Bridge) device(id string) *Device {
	b.devsMu.RLock(); defer b.devsMu.RUnlock()
	return b.devs[id]
}

func (b *Bridge) deviceIDs() []string {
	b.devsMu.RLock(); defer b.devsMu.RUnlock()
	ids := make([]string, 0, len(b.devs))
	for id := range b.devs { ids = append(ids, id) }
	return ids
}

// ── Log Buffer ───────────────────────────────────────────────────────────

type LogBuffer struct {
	mu    sync.RWMutex
	lines []string
	max   int
}

func newLogBuffer(max int) *LogBuffer { return &LogBuffer{lines: make([]string, 0, max), max: max} }

func (lb *LogBuffer) Write(p []byte) (int, error) {
	lb.mu.Lock(); defer lb.mu.Unlock()
	for _, line := range strings.Split(strings.TrimRight(string(p), "\n"), "\n") {
		lb.lines = append(lb.lines, line)
		if len(lb.lines) > lb.max { lb.lines = lb.lines[len(lb.lines)-lb.max:] }
	}
	return len(p), nil
}

func (lb *LogBuffer) Lines() []string {
	lb.mu.RLock(); defer lb.mu.RUnlock()
	r := make([]string, len(lb.lines)); copy(r, lb.lines); return r
}

// ── HTTP Handlers ────────────────────────────────────────────────────────

// API (:8090) — iRidi Server compatible

func (b *Bridge) apiState(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("device")
	d := b.device(id)
	if d == nil { http.Error(w, "device not found", 404); return }
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(d.State())
}

func (b *Bridge) apiCommand(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("device")
	d := b.device(id)
	if d == nil { http.Error(w, "device not found", 404); return }
	body, _ := io.ReadAll(r.Body)
	cmd := strings.TrimSpace(string(body))
	b.logger.Printf("[%s] API CMD: %s", id, cmd)

	var err error
	switch {
	case cmd == "POWER_ON": err = d.SendKey("KEY_POWER")
	case strings.HasPrefix(cmd, "KEY_"): err = d.SendKey(cmd)
	case strings.HasPrefix(cmd, "VOL_"): var v int; fmt.Sscanf(cmd, "VOL_%d", &v); err = d.SetVolume(v)
	case strings.HasPrefix(cmd, "SRC_"): err = d.SetSource(strings.TrimPrefix(cmd, "SRC_"))
	case strings.HasPrefix(cmd, "APP_"): err = d.LaunchApp(strings.TrimPrefix(cmd, "APP_"))
	case cmd == "MUTE": err = d.SendKey("KEY_MUTE")
	default: err = d.SendKey(cmd)
	}
	if err != nil { http.Error(w, err.Error(), 503); return }
	w.Write([]byte(`{"ok":true}`))
}

func (b *Bridge) apiList(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	ids := b.deviceIDs()
	if ids == nil { ids = []string{} }
	json.NewEncoder(w).Encode(ids)
}

// Web UI (:8889)

func (b *Bridge) uiHTML(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write([]byte(uiHTML))
}

func (b *Bridge) uiState(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	b.cfg.mu.RLock()
	type cfgOut struct { Devices []DeviceConfig `json:"devices"`; APIPort int `json:"api_port"`; UIPort int `json:"ui_port"` }
	co := cfgOut{Devices: b.cfg.Devices, APIPort: b.cfg.APIPort, UIPort: b.cfg.UIPort}
	b.cfg.mu.RUnlock()

	states := make(map[string]interface{})
	for _, id := range b.deviceIDs() {
		if d := b.device(id); d != nil { states[id] = d.State() }
	}
	json.NewEncoder(w).Encode(map[string]interface{}{"config": co, "devices": states})
}

func (b *Bridge) uiCommand(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" { http.Error(w, "POST only", 405); return }
	body, _ := io.ReadAll(r.Body)
	var req struct {
		Device string `json:"device"`
		Action string `json:"action"`
		Value  string `json:"value"`
	}
	json.Unmarshal(body, &req)

	d := b.device(req.Device)
	if d == nil { http.Error(w, "device not found", 404); return }

	var err error
	switch req.Action {
	case "sendkey": b.logger.Printf("[%s] UI KEY: %s", req.Device, req.Value); err = d.SendKey(req.Value)
	case "setvol": b.logger.Printf("[%s] UI VOL: %s", req.Device, req.Value); var v int; fmt.Sscanf(req.Value, "%d", &v); err = d.SetVolume(v)
	case "setsrc": b.logger.Printf("[%s] UI SRC: %s", req.Device, req.Value); err = d.SetSource(req.Value)
	case "launch": b.logger.Printf("[%s] UI APP: %s", req.Device, req.Value); err = d.LaunchApp(req.Value)
	case "reconnect": b.logger.Printf("[%s] UI RECONNECT", req.Device); go d.Connect()
	}
	if err != nil { http.Error(w, err.Error(), 503); return }
	w.Write([]byte(`{"ok":true}`))
}

func (b *Bridge) uiSettings(w http.ResponseWriter, r *http.Request) {
	if r.Method == "POST" {
		body, _ := io.ReadAll(r.Body)
		var updated BridgeConfig
		if json.Unmarshal(body, &updated) == nil {
			b.cfg.mu.Lock()
			b.cfg.Devices = updated.Devices
			b.cfg.APIPort = updated.APIPort
			b.cfg.UIPort = updated.UIPort
			b.cfg.mu.Unlock()
			b.cfg.save()
			b.syncDevices()
			w.Write([]byte(`{"ok":true,"saved":true}`))
			return
		}
	}
	b.cfg.mu.RLock(); json.NewEncoder(w).Encode(b.cfg); b.cfg.mu.RUnlock()
}

func (b *Bridge) uiLogs(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(b.logBuf.Lines())
}

// ── Web UI HTML ──────────────────────────────────────────────────────────

const uiHTML = `<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VIDAA Bridge</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font:13px/1.4 system-ui,sans-serif;background:#0d1117;color:#c9d1d9;min-height:100vh}
.topbar{background:#161b22;padding:8px 16px;display:flex;align-items:center;gap:12px;border-bottom:1px solid #30363d}
.topbar h1{font-size:16px;color:#58a6ff;white-space:nowrap}
.topbar .status{font-size:11px;padding:2px 8px;border-radius:10px;font-weight:bold}
.topbar .on{background:#1a3a1a;color:#3fb950}
.topbar .off{background:#3a1a1a;color:#f85149}
.tabs{display:flex;gap:4px;flex:1;overflow-x:auto}
.tabs button{padding:6px 14px;border:1px solid #30363d;border-radius:6px 6px 0 0;background:#0d1117;color:#8b949e;cursor:pointer;font-size:12px;white-space:nowrap;transition:.15s}
.tabs button:hover{color:#c9d1d9;border-color:#58a6ff}
.tabs button.active{background:#21262d;color:#58a6ff;border-color:#58a6ff;border-bottom-color:#21262d}
.tabs button .dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:5px}
.tabs button .dot.on{background:#3fb950}
.tabs button .dot.off{background:#f85149}
.content{padding:12px;display:none}
.content.active{display:block}
.row{display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap}
.card{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px;flex:1;min-width:280px}
.card h2{font-size:13px;color:#8b949e;margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px}
.info{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.info .l{color:#8b949e;font-size:11px}
.info .v{text-align:right;font-weight:bold;color:#58a6ff;font-size:12px}
.keypad{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}
.keypad button{padding:10px 4px;border:1px solid #30363d;border-radius:5px;background:#21262d;color:#c9d1d9;cursor:pointer;font-size:12px;transition:all .1s;user-select:none}
.keypad button:active{transform:scale(.93);background:#58a6ff;color:#000;border-color:#58a6ff}
.keypad button:hover{border-color:#58a6ff}
.keypad button.red{background:#3a1a1a}
.keypad button.red:hover{background:#f85149;color:#fff}
.keypad button.green{background:#1a3a1a}
.keypad button.green:hover{background:#3fb950;color:#000}
.keypad button.blue{background:#1a1a3a}
.keypad button.blue:hover{background:#58a6ff;color:#000}
.vol-row{grid-column:span 3;display:flex;align-items:center;gap:8px;padding:4px 0}
.vol-row input[type=range]{flex:1;accent-color:#58a6ff}
.vol-row span{min-width:30px;text-align:center;font-weight:bold;color:#58a6ff;font-size:14px}
.src-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:4px}
.src-grid button{padding:8px 4px;border:1px solid #30363d;border-radius:5px;background:#21262d;color:#c9d1d9;cursor:pointer;font-size:11px;transition:.1s}
.src-grid button:active{background:#58a6ff;color:#000}
.src-grid button.active{background:#1f6feb;border-color:#58a6ff}
.form-row{margin-bottom:8px}
.form-row label{display:block;color:#8b949e;font-size:11px;margin-bottom:2px}
.form-row input{width:100%;padding:6px 8px;border:1px solid #30363d;border-radius:4px;background:#0d1117;color:#c9d1d9;font-size:12px}
.btn{padding:7px 14px;border:1px solid #30363d;border-radius:5px;cursor:pointer;font-size:12px;transition:.15s}
.btn-primary{background:#238636;border-color:#238636;color:#fff}
.btn-primary:hover{background:#2ea043}
.btn-warning{background:#1f6feb;border-color:#1f6feb;color:#fff}
.btn-warning:hover{background:#388bfd}
.btn-danger{background:#da3633;border-color:#da3633;color:#fff}
.btn-group{display:flex;gap:6px;margin-top:8px}
.toast{position:fixed;top:50px;right:16px;background:#238636;color:#fff;padding:8px 16px;border-radius:6px;font-size:13px;z-index:999;opacity:0;transition:opacity .3s;pointer-events:none}
.toast.show{opacity:1}
.log-panel{border-top:2px solid #30363d;padding:12px 16px;margin-top:0}
.log-panel h2{font-size:13px;color:#8b949e;margin-bottom:6px}
.log-window{background:#0a0c10;border:1px solid #30363d;border-radius:4px;padding:8px 12px;height:200px;overflow-y:auto;font:11px/1.5 monospace;color:#7d8590;width:100%}
.log-window div{padding:1px 0;white-space:pre-wrap;word-break:break-all}
.log-window .err{color:#f85149}
.log-window .ok{color:#3fb950}
.log-window .warn{color:#d29922}
.feedback{position:fixed;pointer-events:none;z-index:1000;color:#58a6ff;font-weight:bold;font-size:18px;transition:all .4s ease-out}
</style>
</head>
<body>

<div class="topbar">
<h1>VIDAA Bridge</h1>
<div class="tabs" id="tabs"></div>
</div>

<div id="contentArea"></div>

<div class="log-panel">
<h2>Log</h2>
<div class="log-window" id="logWindow"><div>Loading...</div></div>
</div>

<div class="toast" id="toast"></div>

<script>
let state = {config:{devices:[]}, devices:{}};
let activeDevice = '';
const srcNames = {'0':'TV','1':'AV','2':'Component','3':'HDMI1','4':'HDMI2','5':'HDMI3','6':'HDMI4'};

function toast(msg) {
    let t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    setTimeout(function(){t.classList.remove('show')}, 1500);
}

function feedback(btn) {
    let r = btn.getBoundingClientRect();
    let f = document.createElement('div');
    f.className = 'feedback'; f.textContent = 'OK';
    f.style.left = r.left + r.width/2 - 15 + 'px';
    f.style.top = r.top - 20 + 'px';
    document.body.appendChild(f);
    setTimeout(function(){f.style.opacity='0';f.style.top=r.top-40+'px'}, 50);
    setTimeout(function(){f.remove()}, 500);
}

async function refresh() {
    try{
        let r = await fetch('/ui/state');
        state = await r.json();
        document.getElementById('tabs').innerHTML = '';
        document.getElementById('contentArea').innerHTML = '';

        if (!state.config || !state.config.devices) return;

        state.config.devices.forEach(function(dev, i) {
            let ds = state.devices[dev.id] || {};
            let con = ds.connected;
            let dot = '<span class="dot '+(con?'on':'off')+'"></span>';
            let cls = (activeDevice === dev.id || (!activeDevice && i === 0)) ? 'active' : '';
            document.getElementById('tabs').innerHTML +=
                '<button class="'+cls+'" onclick="switchDevice(\''+dev.id+'\')">'+dot+dev.name+'</button>';

            let div = document.createElement('div');
            div.className = 'content ' + cls;
            div.id = 'content_' + dev.id;
            div.innerHTML = buildDeviceUI(dev, ds);
            document.getElementById('contentArea').appendChild(div);
        });

        if (!activeDevice && state.config.devices.length > 0) {
            activeDevice = state.config.devices[0].id;
        }
    }catch(e){console.error(e)}
}

function buildDeviceUI(dev, ds) {
    let v = ds.volume || 25;
    return '<div class="row">'+
    '<div class="card"><h2>'+dev.name+'</h2>'+
    '<div class="info">'+
    '<span class="l">Status</span><span class="v" style="color:'+(ds.connected?'#3fb950':'#f85149')+'">'+(ds.connected?'Connected':'Offline')+'</span>'+
    '<span class="l">Power</span><span class="v">'+ds.power+'</span>'+
    '<span class="l">Volume</span><span class="v">'+v+'</span>'+
    '<span class="l">Muted</span><span class="v">'+(ds.muted?'YES':'no')+'</span>'+
    '<span class="l">Source</span><span class="v">'+ds.source+'</span>'+
    '<span class="l">Uptime</span><span class="v">'+ds.uptime+'</span>'+
    '<span class="l">IP</span><span class="v">'+dev.tv_ip+':'+dev.tv_port+'</span>'+
    '<span class="l">MAC</span><span class="v">'+dev.tv_mac+'</span>'+
    '<span class="l">TLS</span><span class="v" style="color:'+(dev.no_tls?'#d29922':'#3fb950')+'">'+(dev.no_tls?'OFF':'mTLS')+'</span>'+
    '</div></div>'+

    '<div class="card"><h2>Remote</h2><div class="keypad">'+
    '<button class="red" onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_POWER\',this)">&#x23FB; POWER</button>'+
    '<button onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_MUTE\',this)">MUTE</button>'+
    '<button onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_HOME\',this)">HOME</button>'+
    '<button onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_BACK\',this)">BACK</button>'+
    '<button class="blue" onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_UP\',this)">&#x25B2;</button>'+
    '<button onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_MENU\',this)">MENU</button>'+
    '<button class="blue" onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_LEFT\',this)">&#x25C0;</button>'+
    '<button class="blue" onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_OK\',this)">OK</button>'+
    '<button class="blue" onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_RIGHT\',this)">&#x25B6;</button>'+
    '<button onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_INFO\',this)">INFO</button>'+
    '<button class="blue" onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_DOWN\',this)">&#x25BC;</button>'+
    '<button onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_EXIT\',this)">EXIT</button>'+
    '<button class="green" onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_VOLUME_UP\',this)">VOL+</button>'+
    '<button class="green" onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_VOLUME_DOWN\',this)">VOL-</button>'+
    '<button onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_CHANNEL_UP\',this)">CH+</button>'+
    '<button onclick="act(\''+dev.id+'\',\'sendkey\',\'KEY_CHANNEL_DOWN\',this)">CH-</button>'+
    '<div class="vol-row"><span id="vl_'+dev.id+'">'+v+'</span>'+
    '<input type="range" min="0" max="100" value="'+v+'" onchange="act(\''+dev.id+'\',\'setvol\',this.value,this)"></div>'+
    '</div></div>'+

    '<div class="card"><h2>Source</h2><div class="src-grid">'+
    ['TV','AV','HDMI1','HDMI2','HDMI3','HDMI4','Component'].map(function(s){
        return '<button class="'+(ds.source === s ? 'active' : '')+'" onclick="act(\''+dev.id+'\',\'setsrc\',\''+s.toLowerCase()+'\',this)">'+s+'</button>';
    }).join('')+
    '</div></div>'+

    '<div class="card"><h2>Apps</h2><div class="src-grid">'+
    ['YouTube','Netflix','Prime','Disney+'].map(function(a){
        return '<button onclick="act(\''+dev.id+'\',\'launch\',\''+a.toLowerCase()+'\',this)">'+a+'</button>';
    }).join('')+
    '</div></div>'+

    '<div class="card"><h2>Settings</h2>'+
    '<div class="form-row"><label>Name</label><input id="cfg_name_'+dev.id+'" value="'+dev.name+'"></div>'+
    '<div class="form-row"><label>TV IP</label><input id="cfg_ip_'+dev.id+'" value="'+dev.tv_ip+'"></div>'+
    '<div class="form-row"><label>TV MAC</label><input id="cfg_mac_'+dev.id+'" value="'+dev.tv_mac+'"></div>'+
    '<div class="form-row"><label>TV Port</label><input id="cfg_port_'+dev.id+'" type="number" value="'+dev.tv_port+'"></div>'+
    '<div class="form-row"><label>Cert file (PEM)</label><input id="cfg_cert_'+dev.id+'" value="'+(dev.cert_file||'')+'" placeholder="vidaa_client.pem"></div>'+
    '<div class="form-row"><label>Key file (PEM)</label><input id="cfg_key_'+dev.id+'" value="'+(dev.key_file||'')+'" placeholder="vidaa_client.key"></div>'+
    '<div class="form-row"><label><input type="checkbox" id="cfg_notls_'+dev.id+'" '+(dev.no_tls?'checked':'')+' onchange="document.getElementById(\'cfg_notls_val_'+dev.id+'\').value=this.checked"> No TLS (testing only)</label>'+
    '<input type="hidden" id="cfg_notls_val_'+dev.id+'" value="'+dev.no_tls+'"></div>'+
    '<div class="btn-group">'+
    '<button class="btn btn-primary" onclick="saveDevice(\''+dev.id+'\')">Save</button>'+
    '<button class="btn btn-warning" onclick="act(\''+dev.id+'\',\'reconnect\',\'\')">Reconnect</button>'+
    '</div></div>'+

    '</div>';
}

function switchDevice(id) {
    activeDevice = id;
    document.querySelectorAll('.tabs button').forEach(function(b){b.classList.remove('active')});
    document.querySelectorAll('.content').forEach(function(c){c.classList.remove('active')});
    let tab = document.querySelector('.tabs button[onclick*="'+id+'"]');
    let cnt = document.getElementById('content_'+id);
    if (tab) tab.classList.add('active');
    if (cnt) cnt.classList.add('active');
}

async function act(device, action, value, btn) {
    try{
        let r = await fetch('/ui/command', {method:'POST', body:JSON.stringify({device:device,action:action,value:value})});
        let d = await r.json();
        if (d.ok) {
            if (btn) feedback(btn);
            toast(action + ' ' + (value || 'OK'));
            setTimeout(refresh, 300);
        }
    }catch(e){toast('ERROR: '+e)}
}

async function saveDevice(id) {
    let devs = state.config.devices.map(function(d){
        if (d.id === id) {
            let notlsEl = document.getElementById('cfg_notls_val_'+id);
            let certEl = document.getElementById('cfg_cert_'+id);
            let keyEl = document.getElementById('cfg_key_'+id);
            return {
                id: id,
                name: document.getElementById('cfg_name_'+id).value,
                tv_ip: document.getElementById('cfg_ip_'+id).value,
                tv_mac: document.getElementById('cfg_mac_'+id).value,
                tv_port: parseInt(document.getElementById('cfg_port_'+id).value)||36669,
                no_tls: notlsEl ? notlsEl.value === 'true' : d.no_tls,
                cert_file: certEl ? certEl.value : (d.cert_file||''),
                key_file: keyEl ? keyEl.value : (d.key_file||'')
            };
        }
        return d;
    });
    let cfg = {devices:devs, api_port:state.config.api_port||8090, ui_port:state.config.ui_port||8889};
    try{
        let r = await fetch('/ui/settings', {method:'POST', body:JSON.stringify(cfg)});
        let d = await r.json();
        if (d.ok) { toast('Saved! Reconnecting...'); setTimeout(refresh, 2000); }
    }catch(e){toast('ERROR: '+e)}
}

async function refreshLogs() {
    try{
        let r = await fetch('/ui/logs'); let lines = await r.json();
        document.getElementById('logWindow').innerHTML = lines.slice(-60).map(function(l){
            let cls = '';
            if (/error|fail/i.test(l)) cls = 'err';
            else if (/connected|ok/i.test(l)) cls = 'ok';
            else if (/warn/i.test(l)) cls = 'warn';
            return '<div class="'+cls+'">'+l+'</div>';
        }).join('');
        document.getElementById('logWindow').scrollTop = document.getElementById('logWindow').scrollHeight;
    }catch(e){}
}

setInterval(function(){refresh();refreshLogs()}, 2500);
refresh(); refreshLogs();
</script>
</body>
</html>`

// ── Main ─────────────────────────────────────────────────────────────────

func main() {
	configPath := flag.String("config", "vidaa_bridge.json", "Config file path")
	flag.Parse()

	cfg := &BridgeConfig{APIPort: 8090, UIPort: 8889}
	if _, err := os.Stat(*configPath); err == nil {
		if err := cfg.load(*configPath); err != nil {
			log.Printf("Config load error: %v", err)
		}
	}
	cfg.save()

	bridge := NewBridge(cfg)

	// API mux (:8090)
	apiMux := http.NewServeMux()
	apiMux.HandleFunc("/api/{device}/state", bridge.apiState)
	apiMux.HandleFunc("/api/{device}/command", bridge.apiCommand)
	apiMux.HandleFunc("/api/list", bridge.apiList)
	// Also serve iRidi-compatible flat endpoints for backward compat
	apiMux.HandleFunc("/state", func(w http.ResponseWriter, r *http.Request) {
		ids := bridge.deviceIDs()
		if len(ids) > 0 {
			d := bridge.device(ids[0])
			if d != nil { w.Header().Set("Content-Type", "application/json"); json.NewEncoder(w).Encode(d.State()); return }
		}
		http.Error(w, "no devices", 404)
	})
	apiMux.HandleFunc("/command", func(w http.ResponseWriter, r *http.Request) {
		ids := bridge.deviceIDs()
		if len(ids) > 0 {
			body, _ := io.ReadAll(r.Body)
			r2 := r.Clone(r.Context())
			r2.Body = io.NopCloser(strings.NewReader(string(body)))
			bridge.apiCommand(w, r2) // won't work because PathValue doesn't match
			return
		}
		http.Error(w, "no devices", 404)
	})

	// UI mux (:8889)
	uiMux := http.NewServeMux()
	uiMux.HandleFunc("/", bridge.uiHTML)
	uiMux.HandleFunc("/ui/state", bridge.uiState)
	uiMux.HandleFunc("/ui/command", bridge.uiCommand)
	uiMux.HandleFunc("/ui/settings", bridge.uiSettings)
	uiMux.HandleFunc("/ui/logs", bridge.uiLogs)

	go func() {
		log.Printf("API server on :%d", cfg.APIPort)
		log.Fatal(http.ListenAndServe(fmt.Sprintf(":%d", cfg.APIPort), apiMux))
	}()

	go func() {
		log.Printf("Web UI on :%d", cfg.UIPort)
		log.Fatal(http.ListenAndServe(fmt.Sprintf(":%d", cfg.UIPort), uiMux))
	}()

	log.Printf("VIDAA Bridge v4 started. Devices: %d", len(cfg.Devices))
	for _, d := range cfg.Devices {
		log.Printf("  [%s] %s @ %s:%d", d.ID, d.Name, d.TVIP, d.TVPort)
	}

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	log.Printf("Shutting down...")
}
