#!/usr/bin/env python3
"""
Minimal OIDC-compatible server for Conjur authn-jwt integration testing.

Provides only the endpoints that Conjur's authn-jwt authenticator needs:

  GET  /.well-known/openid-configuration  — OIDC discovery document
  GET  /.well-known/jwks.json             — RSA public-key set (JWKS)
  POST /token                             — issue a signed RS256 JWT
  GET  /health                            — liveness probe

The /token endpoint accepts a JSON body with a 'claims' dict that is
merged into the JWT payload, letting each test case set any claim it needs.

This is NOT a spec-compliant OAuth2 server; it is purpose-built for testing
Conjur's jwks-uri signature-validation path without any internet access or
browser-based OAuth2 flows.
"""
from __future__ import annotations

import base64
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt as pyjwt

# ── configuration ─────────────────────────────────────────────────────────────
ISSUER = os.environ.get("OIDC_ISSUER", "http://oidc-provider:8080")
PORT   = int(os.environ.get("PORT", "8080"))
KID    = "conjur-test-key-1"

# ── key generation (once at startup) ─────────────────────────────────────────
_private_key     = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_numbers  = _private_key.public_key().public_numbers()


def _b64url(value: int) -> str:
    """Encode a big-endian integer as a base64url string (no padding)."""
    length = (value.bit_length() + 7) // 8
    raw    = value.to_bytes(length, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _private_pem() -> bytes:
    return _private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _jwks() -> dict:
    return {
        "keys": [{
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": KID,
            "n":   _b64url(_public_numbers.n),
            "e":   _b64url(_public_numbers.e),
        }]
    }


def _discovery() -> dict:
    return {
        "issuer":                                ISSUER,
        "jwks_uri":                              f"{ISSUER}/.well-known/jwks.json",
        "id_token_signing_alg_values_supported": ["RS256"],
        "response_types_supported":              ["id_token"],
        "subject_types_supported":               ["public"],
    }


# ── HTTP handler ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[oidc-provider] {self.address_string()} - {fmt % args}", flush=True)

    def _respond(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/.well-known/openid-configuration":
            self._respond(_discovery())
        elif self.path == "/.well-known/jwks.json":
            self._respond(_jwks())
        elif self.path == "/health":
            self._respond({"status": "ok"})
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        if self.path != "/token":
            self.send_error(404, "Not found")
            return

        length  = int(self.headers.get("Content-Length", 0))
        body    = json.loads(self.rfile.read(length) or b"{}")

        now     = int(time.time())
        payload = {
            "iss": ISSUER,
            "iat": now,
            "exp": now + 3600,
            **body.get("claims", {}),
        }

        token = pyjwt.encode(
            payload,
            _private_pem(),
            algorithm="RS256",
            headers={"kid": KID},
        )
        self._respond({"token": token})


if __name__ == "__main__":
    srv = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[oidc-provider] listening on :{PORT}  issuer={ISSUER}", flush=True)
    srv.serve_forever()
