"""Generate self-signed certificates for the VIDAA TV emulator.

Creates:
- CA cert (RemoteCA)
- Server cert (emulates TV's broker cert)
- Client cert (for testing without the original vidaa cert)

Usage: python generate_certs.py
Output: certs/ directory with CA, server, and client certs
"""

import os
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def _generate_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())


def _make_cert(subject_name, issuer_name, subject_key, issuer_key, ca=False):
    builder = x509.CertificateBuilder()
    builder = builder.subject_name(subject_name)
    builder = builder.issuer_name(issuer_name)
    builder = builder.public_key(subject_key.public_key())
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.not_valid_before(datetime.datetime.utcnow())
    builder = builder.not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365 * 10))

    if ca:
        builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        builder = builder.add_extension(x509.KeyUsage(
            key_cert_sign=True, crl_sign=True, digital_signature=False,
            content_commitment=False, key_encipherment=False, data_encipherment=False,
            key_agreement=False, encipher_only=False, decipher_only=False,
        ), critical=True)
    else:
        builder = builder.add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        builder = builder.add_extension(x509.KeyUsage(
            digital_signature=True, key_encipherment=True, key_agreement=True,
            content_commitment=False, data_encipherment=False,
            encipher_only=False, decipher_only=False, crl_sign=False, key_cert_sign=False,
        ), critical=True)
        builder = builder.add_extension(x509.ExtendedKeyUsage([
            x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
        ]), critical=False)

    builder = builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(subject_key.public_key()),
        critical=False,
    )
    if issuer_key:
        builder = builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()),
            critical=False,
        )

    return builder.sign(private_key=issuer_key or subject_key, algorithm=hashes.SHA256(), backend=default_backend())


def main():
    outdir = os.path.join(os.path.dirname(__file__), "certs")
    os.makedirs(outdir, exist_ok=True)

    ca_key = _generate_key()
    ca_name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "shandong"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "qingdao"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "hh"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "multimedia"),
        x509.NameAttribute(NameOID.COMMON_NAME, "RemoteCA"),
    ])
    ca_cert = _make_cert(ca_name, ca_name, ca_key, ca_key, ca=True)

    for fname, data in [("ca_key.pem", ca_key), ("ca_cert.pem", ca_cert)]:
        path = os.path.join(outdir, fname)
        if isinstance(data, rsa.RSAPrivateKey):
            with open(path, "wb") as f:
                f.write(data.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                ))
        else:
            with open(path, "wb") as f:
                f.write(data.public_bytes(serialization.Encoding.PEM))
        print(f"  {fname}")

    server_key = _generate_key()
    server_name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "shandong"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "qingdao"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "hh"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "multimedia"),
        x509.NameAttribute(NameOID.COMMON_NAME, "HisenseTV"),
    ])
    server_cert = _make_cert(server_name, ca_name, server_key, ca_key, ca=False)

    for fname, data in [("server_key.pem", server_key), ("server_cert.pem", server_cert)]:
        path = os.path.join(outdir, fname)
        if isinstance(data, rsa.RSAPrivateKey):
            with open(path, "wb") as f:
                f.write(data.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                ))
        else:
            with open(path, "wb") as f:
                f.write(data.public_bytes(serialization.Encoding.PEM))
        print(f"  {fname}")

    client_key = _generate_key()
    client_name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "shandong"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "hh"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "multimedia"),
        x509.NameAttribute(NameOID.COMMON_NAME, "TestClient"),
    ])
    client_cert = _make_cert(client_name, ca_name, client_key, ca_key, ca=False)

    for fname, data in [("client_key.pem", client_key), ("client_cert.pem", client_cert)]:
        path = os.path.join(outdir, fname)
        if isinstance(data, rsa.RSAPrivateKey):
            with open(path, "wb") as f:
                f.write(data.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                ))
        else:
            with open(path, "wb") as f:
                f.write(data.public_bytes(serialization.Encoding.PEM))
        print(f"  {fname}")

    print(f"\nCertificates generated in: {outdir}")


if __name__ == "__main__":
    main()
