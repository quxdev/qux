"""Infrastructure delivery audit for a single URL endpoint.

Collects HTTP/2, TLS, DNS, compression, security headers, CDN cache,
cookie flags, and certificate metrics.  Can be used standalone or via
the ``site_audit`` management command.

Usage::

    from qux.infra.endpoint import Endpoint

    ep = Endpoint("https://example.com", timeout=10, parse_html=True)
    print(ep.status())   # "PASS", "WARN", or "FAIL"
    print(ep.data)       # dict of all collected metrics
"""

import re
import socket
import ssl
import time
from urllib.parse import urlparse

import httpx

COMPACT_COL_WIDTH = 22
COMPACT_SEPARATOR = " | "

SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Content-Security-Policy",
    "Referrer-Policy",
    "Permissions-Policy",
]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def cell(text):
    """Format a value into a fixed-width compact column."""
    text = "-" if text is None else str(text).strip()
    if len(text) > COMPACT_COL_WIDTH:
        text = text[: COMPACT_COL_WIDTH - 1] + "\u2026"
    return f"{text:<{COMPACT_COL_WIDTH}}"


def fmt_ms(v):
    """Format a value as milliseconds."""
    if v is None:
        return "-"
    return f"{int(round(float(v))):,} ms"


def fmt_pct(v):
    """Format a value as a percentage."""
    if v is None:
        return "-"
    return f"{float(v) * 100:,.2f}%"


def fmt_int(v):
    """Format a value as a comma-separated integer."""
    if v is None:
        return "-"
    return f"{int(v):,}"


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------


def parse_cookie_name(cookie_str):
    """Extract cookie name from a Set-Cookie header value."""
    return cookie_str.split("=", 1)[0].strip()


def check_cookie_flag(cookie_str, flag):
    """Check if a cookie string contains a given flag (case-insensitive)."""
    parts = [p.strip().lower() for p in cookie_str.split(";")]
    return any(p == flag.lower() or p.startswith(flag.lower() + "=") for p in parts)


def get_cookie_attribute(cookie_str, attr):
    """Get the value of a cookie attribute, or None."""
    parts = [p.strip() for p in cookie_str.split(";")]
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            if k.strip().lower() == attr.lower():
                return v.strip()
    return None


# ---------------------------------------------------------------------------
# Endpoint class
# ---------------------------------------------------------------------------


class Endpoint:
    """Collect delivery metrics for a single URL endpoint.

    Probes the given URL via HTTP/2, inspects TLS certificates, resolves
    DNS, measures compression, checks security headers, audits cookies,
    and detects CDN cache behaviour.

    Attributes:
        url: The URL being audited.
        timeout: Request timeout in seconds.
        parse_html: Whether to parse the HTML response for stylesheet/script counts.
        data: Dict of all collected metrics and warnings.
    """

    def __init__(self, url, timeout, parse_html=False):
        self.url = url
        self.timeout = timeout
        self.parse_html = parse_html
        self.data = self._collect()

    # ---------- Public API ----------

    @property
    def warnings(self):
        """Return the list of warnings collected during the audit."""
        return self.data.get("warnings", [])

    def status(self):
        """Return PASS, WARN, or FAIL based on collected warnings."""
        if any("Request failed" in w for w in self.warnings):
            return "FAIL"
        if any("Not using HTTP/2" in w for w in self.warnings):
            return "FAIL"
        if any("Response not compressed" in w for w in self.warnings):
            return "FAIL"
        if self.warnings:
            return "WARN"
        return "PASS"

    def render_compact(self, include_css=False, include_cache=False):
        """Print a compact summary of endpoint metrics."""
        pop_value = f"POP={self.data.get('cf_pop')}"
        if include_cache:
            pop_value = f"{pop_value} | {self.data.get('cf_cache_status')}"

        print(
            cell(self.data.get("http_version"))
            + COMPACT_SEPARATOR
            + cell(self.data.get("tls_version"))
            + COMPACT_SEPARATOR
            + cell(pop_value)
        )

        print(
            cell(f"TTFB={fmt_ms(self.data.get('ttfb_ms'))}")
            + COMPACT_SEPARATOR
            + cell(f"Total={fmt_ms(self.data.get('total_time_ms'))}")
            + COMPACT_SEPARATOR
            + cell(f"Compression={fmt_pct(self.data.get('compression_ratio'))}")
        )

        # Security summary line
        sec_hdrs = self.data.get("security_headers", {})
        present_count = sum(1 for v in sec_hdrs.values() if v is not None)
        total_count = len(sec_hdrs) if sec_hdrs else len(SECURITY_HEADERS)

        cert_exp = self.data.get("cert_expiry_days")
        cert_str = f"{cert_exp}d" if cert_exp is not None else "-"

        redirect_count = len(self.data.get("redirect_chain", []))

        dns_ms = self.data.get("dns_resolve_ms")
        dns_str = f"{int(dns_ms)}ms" if dns_ms is not None else "-"

        print(
            cell(f"SecHdrs={present_count}/{total_count}")
            + COMPACT_SEPARATOR
            + cell(f"CertExp={cert_str}")
            + COMPACT_SEPARATOR
            + cell(f"Redirects={redirect_count}")
        )

        output_line = cell(f"DNS={dns_str}")
        if include_css:
            cell_b = cell(f"CSS={fmt_int(self.data.get('stylesheet_count'))}")
            cell_c = cell(
                f"BlockingJS={fmt_int(self.data.get('blocking_script_count'))}"
            )
            output_line += COMPACT_SEPARATOR + cell_b + COMPACT_SEPARATOR + cell_c
        print(output_line)

    def render_warnings(self, label):
        """Print warnings if any exist, return True if warnings were printed."""
        if not self.warnings:
            return False

        print(f"\nWarnings: {label}")
        for w in self.warnings:
            print(f"- {w}")
        return True

    # ---------- Internal ----------

    def _collect(
        self,
    ):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        """Collect all delivery metrics for this endpoint."""
        parsed = urlparse(self.url)
        hostname = parsed.hostname

        data = {
            "url": self.url,
            "http_version": None,
            "status_code": None,
            "tls_version": None,
            "ip_address": None,
            "content_encoding": None,
            "mime_type": None,
            "cache_control": None,
            "cf_cache_status": None,
            "cf_pop": None,
            "ttfb_ms": None,
            "total_time_ms": None,
            "compressed_bytes": None,
            "uncompressed_bytes": None,
            "compression_ratio": None,
            "stylesheet_count": None,
            "blocking_script_count": None,
            "cdn_trace": {},
            "security_headers": {},
            "cert_expiry_days": None,
            "cert_issuer": None,
            "cert_san": [],
            "hsts_preload_ready": None,
            "redirect_chain": [],
            "final_url": None,
            "cookie_issues": [],
            "ipv6_address": None,
            "dns_a_count": None,
            "dns_resolve_ms": None,
            "age": None,
            "vary": None,
            "warnings": [],
        }

        try:
            with httpx.Client(http2=True, timeout=self.timeout) as client:
                start = time.time()
                response = self._follow_redirects(client, self.url, data)
                total_time = time.time() - start

                self._extract_response_data(response, data, total_time)
                self._check_cookies(response, data)

                compressed, uncompressed, ratio = self._measure_compression(
                    client, self.url
                )
                data["compressed_bytes"] = compressed
                data["uncompressed_bytes"] = uncompressed
                data["compression_ratio"] = ratio

                if self.parse_html and "text/html" in (data["mime_type"] or ""):
                    self._parse_html_metrics(response.text, data)

                self._resolve_dns(hostname, data)
                self._inspect_tls(hostname, data)
                self._fetch_cdn_trace(client, hostname, data)

            self._generate_warnings(hostname, data)

        except (httpx.HTTPError, socket.gaierror, ssl.SSLError, OSError) as e:
            data["warnings"].append(f"Request failed: {str(e)}")

        return data

    @staticmethod
    def _extract_response_data(response, data, total_time):
        """Extract basic response metrics from the HTTP response."""
        data["http_version"] = response.http_version
        data["status_code"] = response.status_code
        data["content_encoding"] = response.headers.get("content-encoding")
        data["mime_type"] = response.headers.get("content-type")
        data["cache_control"] = response.headers.get("cache-control")
        data["cf_cache_status"] = response.headers.get("cf-cache-status")
        data["ttfb_ms"] = round(response.elapsed.total_seconds() * 1000, 2)
        data["total_time_ms"] = round(total_time * 1000, 2)

        cf_ray = response.headers.get("cf-ray")
        if cf_ray and "-" in cf_ray:
            data["cf_pop"] = cf_ray.split("-")[-1].strip()

        for header_name in SECURITY_HEADERS:
            data["security_headers"][header_name] = response.headers.get(header_name)

        age_val = response.headers.get("age")
        if age_val is not None:
            try:
                data["age"] = int(age_val)
            except ValueError:
                pass
        data["vary"] = response.headers.get("vary")

    @staticmethod
    def _parse_html_metrics(html, data):
        """Count stylesheets and blocking scripts in HTML."""
        data["stylesheet_count"] = len(
            re.findall(r'<link[^>]+rel=["\']stylesheet["\']', html, re.I)
        )
        data["blocking_script_count"] = len(
            re.findall(r"<script(?![^>]+defer)[^>]*>", html, re.I)
        )

    @staticmethod
    def _inspect_tls(hostname, data):
        """Inspect TLS certificate for version, expiry, issuer, and SANs."""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    data["tls_version"] = ssock.version()

                    cert = ssock.getpeercert()
                    if cert:
                        not_after = cert.get("notAfter")
                        if not_after:
                            expiry_ts = ssl.cert_time_to_seconds(not_after)
                            data["cert_expiry_days"] = int(
                                (expiry_ts - time.time()) / 86400
                            )

                        issuer = cert.get("issuer", ())
                        for rdn in issuer:
                            for attr_type, attr_value in rdn:
                                if attr_type == "organizationName":
                                    data["cert_issuer"] = attr_value

                        sans = cert.get("subjectAltName", ())
                        data["cert_san"] = [
                            value for type_, value in sans if type_ == "DNS"
                        ]

        except (httpx.HTTPError, socket.gaierror, ssl.SSLError, OSError) as e:
            data["warnings"].append(f"Network failure: {str(e)}")

    @staticmethod
    def _fetch_cdn_trace(client, hostname, data):
        """Fetch Cloudflare CDN trace data."""
        trace_url = f"https://{hostname}/cdn-cgi/trace"
        try:
            trace_resp = client.get(trace_url)
            if trace_resp.status_code == 200:
                trace_data = {}
                for line in trace_resp.text.strip().splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        trace_data[k] = v
                data["cdn_trace"] = trace_data
        except (httpx.HTTPError, socket.gaierror, ssl.SSLError, OSError) as e:
            data["warnings"].append(f"Network failure: {str(e)}")

    def _generate_warnings(self, hostname, data):
        """Analyze collected data and generate warning messages."""
        if data["http_version"] != "HTTP/2":
            data["warnings"].append("Not using HTTP/2")

        if not data["content_encoding"]:
            data["warnings"].append("Response not compressed")

        if data["ttfb_ms"] and data["ttfb_ms"] > 500:
            data["warnings"].append("High TTFB")

        if self.parse_html:
            if data["stylesheet_count"] and data["stylesheet_count"] > 3:
                data["warnings"].append("Too many blocking stylesheets")
            if data["blocking_script_count"] and data["blocking_script_count"] > 0:
                data["warnings"].append("Blocking <script> without defer detected")
            if data["uncompressed_bytes"] and data["uncompressed_bytes"] > 150_000:
                data["warnings"].append("Large HTML payload")

        self._warn_security_headers(data)
        self._warn_certificate(hostname, data)
        self._warn_hsts_preload(data)

        if len(data["redirect_chain"]) > 2:
            data["warnings"].append(
                f"{len(data['redirect_chain'])} redirects before final response"
            )

        if data["dns_resolve_ms"] is not None and data["dns_resolve_ms"] > 100:
            data["warnings"].append(
                f"Slow DNS resolution ({int(data['dns_resolve_ms'])}ms)"
            )

        if data["vary"] == "*":
            data["warnings"].append("Vary: * defeats caching")

        cf_status = data["cf_cache_status"]
        mime = data["mime_type"] or ""
        if cf_status and cf_status.upper() == "DYNAMIC" and "text/html" not in mime:
            data["warnings"].append("CDN not caching static asset")

    @staticmethod
    def _warn_security_headers(data):
        """Add warnings for missing or misconfigured security headers."""
        for header_name in SECURITY_HEADERS:
            value = data["security_headers"].get(header_name)
            if value is None:
                data["warnings"].append(f"Missing Header: {header_name}")
            elif header_name == "X-Content-Type-Options" and value.lower() != "nosniff":
                data["warnings"].append(
                    f"X-Content-Type-Options is '{value}', expected 'nosniff'"
                )

    @staticmethod
    def _warn_certificate(hostname, data):
        """Add warnings for certificate expiry and SAN mismatches."""
        if data["cert_expiry_days"] is not None and data["cert_expiry_days"] < 14:
            data["warnings"].append(
                f"TLS certificate expires in {data['cert_expiry_days']} days"
            )

        if data["cert_san"] and hostname not in data["cert_san"]:
            matched = any(
                san.startswith("*.") and hostname.endswith(san[1:])
                for san in data["cert_san"]
            )
            if not matched:
                data["warnings"].append("Hostname not in certificate SANs")

    @staticmethod
    def _warn_hsts_preload(data):
        """Check HSTS preload readiness."""
        hsts_value = data["security_headers"].get("Strict-Transport-Security")
        if hsts_value:
            hsts_lower = hsts_value.lower()
            hsts_parts = [p.strip() for p in hsts_lower.split(";")]
            max_age_ok = False
            for part in hsts_parts:
                if part.startswith("max-age="):
                    try:
                        age_val = int(part.split("=", 1)[1])
                        max_age_ok = age_val >= 31536000
                    except ValueError:
                        pass
            has_subdomains = "includesubdomains" in hsts_parts
            has_preload = "preload" in hsts_parts
            data["hsts_preload_ready"] = max_age_ok and has_subdomains and has_preload

    @staticmethod
    def _follow_redirects(client, url, data):
        """Follow redirects manually, recording the chain."""
        max_hops = 10
        current_url = url
        response = None

        for _ in range(max_hops):
            response = client.get(current_url, follow_redirects=False)
            if response.is_redirect:
                data["redirect_chain"].append(
                    {"url": current_url, "status": response.status_code}
                )
                location = response.headers.get("location", "")
                if location.startswith("/"):
                    parsed = urlparse(current_url)
                    location = f"{parsed.scheme}://{parsed.netloc}{location}"
                current_url = location
            else:
                break

        data["final_url"] = current_url
        return response

    @staticmethod
    def _check_cookies(response, data):
        """Check Set-Cookie headers for security flag issues."""
        raw_headers = response.headers.multi_items()
        cookies = [v for k, v in raw_headers if k.lower() == "set-cookie"]

        is_https = str(response.url).startswith("https")
        session_names = {"sessionid", "csrftoken"}

        for cookie_str in cookies:
            name = parse_cookie_name(cookie_str)
            has_secure = check_cookie_flag(cookie_str, "secure")
            has_httponly = check_cookie_flag(cookie_str, "httponly")
            samesite = get_cookie_attribute(cookie_str, "samesite")

            if is_https and not has_secure:
                issue = f'Cookie "{name}" missing Secure flag'
                data["cookie_issues"].append(issue)
                data["warnings"].append(issue)

            if name.lower() in session_names and not has_httponly:
                issue = f'Cookie "{name}" missing HttpOnly flag'
                data["cookie_issues"].append(issue)
                data["warnings"].append(issue)

            if samesite and samesite.lower() == "none" and not has_secure:
                issue = f'Cookie "{name}" has SameSite=None without Secure'
                data["cookie_issues"].append(issue)
                data["warnings"].append(issue)

    @staticmethod
    def _resolve_dns(hostname, data):
        """Resolve DNS with timing and IPv6 detection."""
        try:
            start = time.time()
            results = socket.getaddrinfo(
                hostname, 443, socket.AF_INET, socket.SOCK_STREAM
            )
            elapsed = (time.time() - start) * 1000
            data["dns_resolve_ms"] = round(elapsed, 2)

            if results:
                data["ip_address"] = results[0][4][0]
                data["dns_a_count"] = len(results)
        except (socket.gaierror, OSError) as e:
            data["warnings"].append(f"Network failure: {str(e)}")

        try:
            results_v6 = socket.getaddrinfo(
                hostname, 443, socket.AF_INET6, socket.SOCK_STREAM
            )
            if results_v6:
                data["ipv6_address"] = results_v6[0][4][0]
        except (socket.gaierror, OSError):
            pass

    @staticmethod
    def _measure_compression(client, url):
        """Measure compressed vs uncompressed response sizes."""
        compressed_bytes = None
        uncompressed_bytes = None

        try:
            with client.stream(
                "GET",
                url,
                headers={"Accept-Encoding": "gzip"},
            ) as resp:
                resp.read()
                compressed_bytes = resp.num_bytes_downloaded
        except httpx.HTTPError:
            pass

        try:
            with client.stream(
                "GET",
                url,
                headers={"Accept-Encoding": "identity"},
            ) as resp:
                resp.read()
                uncompressed_bytes = resp.num_bytes_downloaded
        except httpx.HTTPError:
            pass

        ratio = None
        if compressed_bytes and uncompressed_bytes:
            ratio = round(compressed_bytes / uncompressed_bytes, 3)

        return compressed_bytes, uncompressed_bytes, ratio
