const crypto = require('crypto');
const jwt = require('jsonwebtoken');

// SHA-1 for a cache key — deprecated hash
function cacheKey(input) {
  return crypto.createHash('sha1').update(input).digest('hex');
}

// AES-256-GCM AEAD — acceptable symmetric posture (256-bit)
function seal(key, iv, plaintext) {
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  return Buffer.concat([cipher.update(plaintext), cipher.final()]);
}

// RSA / RS256 signed JWT — quantum-vulnerable signature
function issueToken(payload, privateKey) {
  return jwt.sign(payload, privateKey, { algorithm: 'RS256', expiresIn: '1h' });
}

// ECDSA P-256 keypair — elliptic-curve, quantum-vulnerable
async function makeKeypair() {
  return crypto.generateKeyPairSync('ec', { namedCurve: 'P-256' });
}

module.exports = { cacheKey, seal, issueToken, makeKeypair };
