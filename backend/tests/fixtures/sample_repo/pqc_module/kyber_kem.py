"""Already-migrated component: ML-KEM (Kyber) key establishment via liboqs."""
import oqs


def establish_key():
    # ML-KEM-768 - post-quantum, quantum-safe target state
    with oqs.KeyEncapsulation("ML-KEM-768") as kem:
        public_key = kem.generate_keypair()
        ciphertext, shared_secret = kem.encap_secret(public_key)
        return ciphertext, shared_secret
