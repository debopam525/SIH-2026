package main

import (
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/md5"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"fmt"
)

func legacyDigest(b []byte) string {
	return fmt.Sprintf("%x", md5.Sum(b)) // MD5 - broken
}

func newRSAKey() (*rsa.PrivateKey, error) {
	return rsa.GenerateKey(rand.Reader, 2048) // RSA-2048 - Shor-vulnerable
}

func newECKey() (*ecdsa.PrivateKey, error) {
	return ecdsa.GenerateKey(elliptic.P256(), rand.Reader) // ECDSA P-256
}

func serverTLS() *tls.Config {
	return &tls.Config{MinVersion: tls.VersionTLS12} // TLS container
}
