"""CreateX AI - Proxy Trust & Client IP Extraction Test Suite

Verifies:
1. Forged X-Forwarded-For from an untrusted peer is ignored.
2. Valid forwarded IP from a trusted proxy is honored.
3. Malformed forwarded headers are safely ignored.
4. IPv4 and IPv6 (both in proxy CIDR and client address) work correctly.
5. Missing client address safely falls back to '127.0.0.1'.
6. Multiple forwarded addresses are traversed right-to-left to find the real untrusted client.
7. Empty trusted-proxy configuration ignores all forwarded headers.
"""
import sys
from unittest.mock import MagicMock

# Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.core.config import settings
from app.core.rate_limiter import RateLimiter, is_trusted_proxy

results = {"passed": 0, "failed": 0}


def log_test(name: str, passed: bool, detail: str = ""):
    if passed:
        results["passed"] += 1
        print(f"  [PASS] {name}" + (f" -> {detail}" if detail else ""))
    else:
        results["failed"] += 1
        print(f"  [FAIL] {name}" + (f" -> {detail}" if detail else ""))


print("=" * 70)
print("  CreateX AI - Proxy Trust & Client IP Extraction Verification")
print("=" * 70)

limiter = RateLimiter("campaign")


def make_request(peer_host=None, forwarded_header=None):
    req = MagicMock()
    req.headers = {}
    if forwarded_header is not None:
        req.headers["X-Forwarded-For"] = forwarded_header
    if peer_host is not None:
        req.client = MagicMock()
        req.client.host = peer_host
    else:
        req.client = None
    return req


# 1. Empty trusted-proxy configuration
settings.trusted_proxies = ""
req1 = make_request(peer_host="198.51.100.5", forwarded_header="203.0.113.195")
ip1 = limiter._get_client_ip(req1)
log_test(
    "Empty trusted-proxy configuration ignores X-Forwarded-For",
    ip1 == "198.51.100.5",
    f"got={ip1}, expected=198.51.100.5",
)

# 2. Forged X-Forwarded-For from an untrusted peer
settings.trusted_proxies = "10.0.0.0/8,127.0.0.1,::1"
req2 = make_request(peer_host="198.51.100.50", forwarded_header="203.0.113.195")
ip2 = limiter._get_client_ip(req2)
log_test(
    "Forged X-Forwarded-For from untrusted peer ignored",
    ip2 == "198.51.100.50",
    f"got={ip2}, expected=198.51.100.50",
)

# 3. Valid forwarded IP from a trusted proxy (IPv4 CIDR)
settings.trusted_proxies = "10.0.0.0/8,172.16.0.0/12,127.0.0.1"
req3 = make_request(peer_host="10.0.1.5", forwarded_header="203.0.113.195")
ip3 = limiter._get_client_ip(req3)
log_test(
    "Valid forwarded IP from trusted proxy honored",
    ip3 == "203.0.113.195",
    f"got={ip3}, expected=203.0.113.195",
)

# 4. Malformed forwarded headers
req4 = make_request(peer_host="10.0.1.5", forwarded_header="malicious; DROP TABLE;--, not_an_ip")
ip4 = limiter._get_client_ip(req4)
log_test(
    "Malformed forwarded headers ignored, falls back to peer host",
    ip4 == "10.0.1.5",
    f"got={ip4}, expected=10.0.1.5",
)

# 5. IPv4 and IPv6 support
settings.trusted_proxies = "2001:db8:abcd::/48,127.0.0.1"
# Trusted IPv6 proxy forwarding IPv6 client
req5_v6 = make_request(peer_host="2001:db8:abcd::1", forwarded_header="2001:db8:cafe::42")
ip5_v6 = limiter._get_client_ip(req5_v6)
log_test(
    "IPv6 trusted proxy forwarding IPv6 client address",
    ip5_v6 == "2001:db8:cafe::42",
    f"got={ip5_v6}, expected=2001:db8:cafe::42",
)

# Trusted IPv6 proxy forwarding IPv4 client
req5_v4 = make_request(peer_host="2001:db8:abcd::1", forwarded_header="198.51.100.77")
ip5_v4 = limiter._get_client_ip(req5_v4)
log_test(
    "IPv6 trusted proxy forwarding IPv4 client address",
    ip5_v4 == "198.51.100.77",
    f"got={ip5_v4}, expected=198.51.100.77",
)

# 6. Missing client address falls back safely to 127.0.0.1
req6 = make_request(peer_host=None, forwarded_header="203.0.113.195")
ip6 = limiter._get_client_ip(req6)
log_test(
    "Missing client address safely defaults to 127.0.0.1",
    ip6 == "127.0.0.1",
    f"got={ip6}, expected=127.0.0.1",
)

# 7. Multiple forwarded addresses (right-to-left traversal through proxy chain)
settings.trusted_proxies = "10.0.0.0/8,172.16.0.0/12,127.0.0.1"
# Client 203.0.113.88 connects to Proxy1 (172.16.0.5), which forwards to Proxy2 (10.0.0.1)
# Attacker might prepend spoofed IP "1.1.1.1": "1.1.1.1, 203.0.113.88, 172.16.0.5"
req7 = make_request(peer_host="10.0.0.1", forwarded_header="1.1.1.1, 203.0.113.88, 172.16.0.5")
ip7 = limiter._get_client_ip(req7)
log_test(
    "Multiple forwarded addresses traverse right-to-left to untrusted client",
    ip7 == "203.0.113.88",
    f"got={ip7}, expected=203.0.113.88",
)

# 8. All forwarded addresses are trusted proxies
req8 = make_request(peer_host="10.0.0.1", forwarded_header="10.0.0.2, 172.16.0.5")
ip8 = limiter._get_client_ip(req8)
log_test(
    "All forwarded addresses are proxies -> returns leftmost valid proxy",
    ip8 == "10.0.0.2",
    f"got={ip8}, expected=10.0.0.2",
)

# 9. Direct helper function is_trusted_proxy checks
log_test(
    "is_trusted_proxy CIDR match",
    is_trusted_proxy("10.254.12.3", "10.0.0.0/8,192.168.1.1"),
)
log_test(
    "is_trusted_proxy single IP match",
    is_trusted_proxy("192.168.1.1", "10.0.0.0/8,192.168.1.1"),
)
log_test(
    "is_trusted_proxy non-match",
    not is_trusted_proxy("192.168.1.2", "10.0.0.0/8,192.168.1.1"),
)
log_test(
    "is_trusted_proxy malformed input handling",
    not is_trusted_proxy("not_an_ip", "10.0.0.0/8,malformed_cidr"),
)

# Reset settings to default
settings.trusted_proxies = ""

print("=" * 70)
print(f"  Proxy Trust Results: {results['passed']} passed, {results['failed']} failed")
print("=" * 70)

if results["failed"] > 0:
    sys.exit(1)
