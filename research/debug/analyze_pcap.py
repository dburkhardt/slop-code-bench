#!/usr/bin/env python3
"""Analyze a pcap file to extract TCP/TLS connection timing.

Since HTTPS traffic is encrypted, this script focuses on TCP-level
timing visible without decryption:

  - SYN/SYN-ACK latency (connection establishment time)
  - Per-connection data transfer volumes (bytes in each direction)
  - Connection reuse patterns (how many connections, how long each)
  - Idle gaps between data transfers on each connection

The script parses pcap files using the stdlib ``struct`` module
(no external dependencies like scapy). It reads the pcap global
header and per-packet headers, then extracts IP and TCP fields to
reconstruct per-connection timelines.

Usage:
    python3 analyze_pcap.py <pcap_file> [--port 443] [--output FILE]

Arguments:
    pcap_file     Path to the pcap file captured by tcpdump
    --port PORT   Filter to connections involving this port (default: 443)
    --output FILE Write results to FILE instead of stdout

Output:
    Per-connection timing summary including establishment time,
    duration, data volume, packet counts, and idle gap analysis.

Example:
    python3 analyze_pcap.py results/capture.pcap --port 443
    python3 analyze_pcap.py results/capture.pcap --output results/network_analysis.txt
"""
from __future__ import annotations

import argparse
import struct
import sys
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field

# TCP flag constants
TCP_SYN = 0x02
TCP_ACK = 0x10
TCP_FIN = 0x01
TCP_RST = 0x04

# Pcap link-layer types
LINKTYPE_ETHERNET = 1
LINKTYPE_RAW = 101
LINKTYPE_LINUX_SLL = 113
LINKTYPE_LINUX_SLL2 = 276


@dataclass
class Connection:
    """Track state for one TCP connection (4-tuple)."""

    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    syn_time: float | None = None
    synack_time: float | None = None
    first_data_time: float | None = None
    last_data_time: float | None = None
    fin_time: float | None = None
    bytes_to_server: int = 0
    bytes_to_client: int = 0
    packets_to_server: int = 0
    packets_to_client: int = 0
    data_timestamps: list[float] = field(default_factory=list)


def parse_pcap_header(f):
    """Read and validate the pcap global header.

    Returns (byte_order, link_type) where byte_order is '>' or '<'.
    """
    magic = f.read(4)
    if len(magic) < 4:
        raise ValueError("File too short to be a pcap")

    magic_val = struct.unpack(">I", magic)[0]
    if magic_val == 0xA1B2C3D4:
        byte_order = ">"
    elif magic_val == 0xD4C3B2A1:
        byte_order = "<"
    else:
        raise ValueError(
            f"Not a pcap file (magic: 0x{magic_val:08X})"
        )

    header_rest = f.read(20)
    if len(header_rest) < 20:
        raise ValueError("Truncated pcap global header")

    _ver_major, _ver_minor, _thiszone, _sigfigs, _snaplen, link_type = (
        struct.unpack(f"{byte_order}HHIIII", header_rest)
    )
    return byte_order, link_type


def read_packets(f, byte_order):
    """Yield (timestamp_sec, packet_data) for each packet."""
    pkt_hdr_fmt = f"{byte_order}IIII"
    pkt_hdr_size = struct.calcsize(pkt_hdr_fmt)

    while True:
        hdr_data = f.read(pkt_hdr_size)
        if len(hdr_data) < pkt_hdr_size:
            break

        ts_sec, ts_usec, incl_len, _orig_len = struct.unpack(
            pkt_hdr_fmt, hdr_data
        )
        timestamp = ts_sec + ts_usec / 1_000_000.0

        pkt_data = f.read(incl_len)
        if len(pkt_data) < incl_len:
            break

        yield timestamp, pkt_data


def skip_link_layer(pkt_data, link_type):
    """Strip the link-layer header; return the IP payload or None."""
    if link_type == LINKTYPE_ETHERNET:
        if len(pkt_data) < 14:
            return None
        ethertype = struct.unpack(">H", pkt_data[12:14])[0]
        if ethertype == 0x0800:
            return pkt_data[14:]
        return None
    if link_type == LINKTYPE_RAW:
        return pkt_data
    if link_type == LINKTYPE_LINUX_SLL:
        if len(pkt_data) < 16:
            return None
        ethertype = struct.unpack(">H", pkt_data[14:16])[0]
        if ethertype == 0x0800:
            return pkt_data[16:]
        return None
    if link_type == LINKTYPE_LINUX_SLL2:
        if len(pkt_data) < 20:
            return None
        ethertype = struct.unpack(">H", pkt_data[0:2])[0]
        if ethertype == 0x0800:
            return pkt_data[20:]
        return None
    return None


def parse_ip_tcp(ip_payload):
    """Extract IP + TCP fields. Returns dict or None."""
    if ip_payload is None or len(ip_payload) < 20:
        return None

    version_ihl = ip_payload[0]
    version = (version_ihl >> 4) & 0xF
    if version != 4:
        return None

    ihl = (version_ihl & 0xF) * 4
    total_len = struct.unpack(">H", ip_payload[2:4])[0]
    protocol = ip_payload[9]
    if protocol != 6:  # TCP only
        return None

    src_ip = ".".join(str(b) for b in ip_payload[12:16])
    dst_ip = ".".join(str(b) for b in ip_payload[16:20])

    tcp_start = ihl
    if len(ip_payload) < tcp_start + 20:
        return None

    tcp_data = ip_payload[tcp_start:]
    src_port, dst_port, _seq, _ack, offset_flags = struct.unpack(
        ">HHIIH", tcp_data[:14]
    )
    data_offset = ((offset_flags >> 12) & 0xF) * 4
    flags = offset_flags & 0x3F

    payload_len = total_len - ihl - data_offset
    if payload_len < 0:
        payload_len = 0

    return {
        "src_ip": src_ip,
        "src_port": src_port,
        "dst_ip": dst_ip,
        "dst_port": dst_port,
        "flags": flags,
        "payload_len": payload_len,
    }


def connection_key(pkt):
    """Canonical key for a TCP connection (sorted 4-tuple)."""
    a = (pkt["src_ip"], pkt["src_port"])
    b = (pkt["dst_ip"], pkt["dst_port"])
    return tuple(sorted([a, b]))


def is_to_server(pkt, port_filter):
    """True if packet goes toward the server (port_filter)."""
    return pkt["dst_port"] == port_filter


def analyze_pcap(filepath, port_filter=443):
    """Parse a pcap and return per-connection summaries."""
    connections = defaultdict(
        lambda: Connection("", 0, "", 0)
    )

    from pathlib import Path

    with Path(filepath).open("rb") as f:
        byte_order, link_type = parse_pcap_header(f)

        for timestamp, pkt_data in read_packets(f, byte_order):
            ip_payload = skip_link_layer(pkt_data, link_type)
            pkt = parse_ip_tcp(ip_payload)
            if pkt is None:
                continue

            # Filter to connections involving our target port
            if (
                pkt["src_port"] != port_filter
                and pkt["dst_port"] != port_filter
            ):
                continue

            key = connection_key(pkt)
            conn = connections[key]

            # Initialize connection endpoints from SYN
            if conn.src_ip == "":
                if is_to_server(pkt, port_filter):
                    conn.src_ip = pkt["src_ip"]
                    conn.src_port = pkt["src_port"]
                    conn.dst_ip = pkt["dst_ip"]
                    conn.dst_port = pkt["dst_port"]
                else:
                    conn.src_ip = pkt["dst_ip"]
                    conn.src_port = pkt["dst_port"]
                    conn.dst_ip = pkt["src_ip"]
                    conn.dst_port = pkt["src_port"]

            flags = pkt["flags"]

            # Track SYN / SYN-ACK
            if (flags & TCP_SYN) and not (flags & TCP_ACK):
                if conn.syn_time is None:
                    conn.syn_time = timestamp
            elif (
                (flags & TCP_SYN)
                and (flags & TCP_ACK)
                and conn.synack_time is None
            ):
                conn.synack_time = timestamp

            # Track FIN
            if flags & TCP_FIN:
                conn.fin_time = timestamp

            # Track data
            if pkt["payload_len"] > 0:
                if conn.first_data_time is None:
                    conn.first_data_time = timestamp
                conn.last_data_time = timestamp
                conn.data_timestamps.append(timestamp)

                if is_to_server(pkt, port_filter):
                    conn.bytes_to_server += pkt["payload_len"]
                    conn.packets_to_server += 1
                else:
                    conn.bytes_to_client += pkt["payload_len"]
                    conn.packets_to_client += 1

    return dict(connections)


def compute_idle_gaps(timestamps, threshold=1.0):
    """Find gaps > threshold seconds between data packets."""
    if len(timestamps) < 2:
        return []
    gaps = []
    sorted_ts = sorted(timestamps)
    for i in range(1, len(sorted_ts)):
        gap = sorted_ts[i] - sorted_ts[i - 1]
        if gap >= threshold:
            gaps.append((sorted_ts[i - 1], sorted_ts[i], gap))
    return gaps


def format_timestamp(ts):
    """Format a Unix timestamp as HH:MM:SS.mmm."""
    import time as _time

    t = _time.gmtime(ts)
    ms = int((ts % 1) * 1000)
    return f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{ms:03d}"


def format_results(connections, port_filter):
    """Format connection analysis as a readable report."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"TCP Connection Analysis (port {port_filter})")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Total connections: {len(connections)}")
    lines.append("")

    sorted_conns = sorted(
        connections.values(),
        key=lambda c: c.syn_time or c.first_data_time or 0,
    )

    for i, conn in enumerate(sorted_conns, 1):
        lines.append("-" * 70)
        lines.append(f"Connection {i}:")
        lines.append(
            f"  Client: {conn.src_ip}:{conn.src_port}"
        )
        lines.append(
            f"  Server: {conn.dst_ip}:{conn.dst_port}"
        )

        # Establishment timing
        if conn.syn_time and conn.synack_time:
            rtt = (conn.synack_time - conn.syn_time) * 1000
            lines.append(
                f"  SYN->SYN-ACK latency: {rtt:.1f} ms"
            )
            lines.append(
                f"  SYN at:      {format_timestamp(conn.syn_time)}"
            )
            lines.append(
                f"  SYN-ACK at:  {format_timestamp(conn.synack_time)}"
            )
        elif conn.syn_time:
            lines.append(
                f"  SYN at: {format_timestamp(conn.syn_time)}"
                " (no SYN-ACK captured)"
            )

        # Duration
        start = conn.syn_time or conn.first_data_time
        end = conn.fin_time or conn.last_data_time
        if start and end:
            duration = end - start
            lines.append(f"  Duration: {duration:.1f}s")
            lines.append(
                f"  Start: {format_timestamp(start)}"
            )
            lines.append(
                f"  End:   {format_timestamp(end)}"
            )

        # Data volumes
        total_bytes = (
            conn.bytes_to_server + conn.bytes_to_client
        )
        total_pkts = (
            conn.packets_to_server + conn.packets_to_client
        )
        lines.append(f"  Data to server: "
                      f"{conn.bytes_to_server:,} bytes "
                      f"({conn.packets_to_server} packets)")
        lines.append(f"  Data to client: "
                      f"{conn.bytes_to_client:,} bytes "
                      f"({conn.packets_to_client} packets)")
        lines.append(
            f"  Total: {total_bytes:,} bytes "
            f"({total_pkts} packets)"
        )

        # Idle gap analysis
        gaps = compute_idle_gaps(
            conn.data_timestamps, threshold=2.0
        )
        if gaps:
            lines.append(
                f"  Idle gaps (>2s): {len(gaps)}"
            )
            for g_start, g_end, g_dur in gaps[:10]:
                lines.append(
                    f"    {format_timestamp(g_start)} -> "
                    f"{format_timestamp(g_end)} "
                    f"({g_dur:.1f}s)"
                )
            if len(gaps) > 10:
                lines.append(
                    f"    ... and {len(gaps) - 10} more"
                )
        else:
            lines.append("  Idle gaps (>2s): none")

        lines.append("")

    # Summary
    lines.append("=" * 70)
    lines.append("Summary")
    lines.append("=" * 70)

    all_gaps = []
    for conn in sorted_conns:
        all_gaps.extend(
            compute_idle_gaps(conn.data_timestamps, threshold=2.0)
        )

    if all_gaps:
        gap_durations = [g[2] for g in all_gaps]
        lines.append(
            f"Total idle gaps (>2s): {len(all_gaps)}"
        )
        lines.append(
            f"  Min gap: {min(gap_durations):.1f}s"
        )
        lines.append(
            f"  Max gap: {max(gap_durations):.1f}s"
        )
        lines.append(
            f"  Mean gap: "
            f"{sum(gap_durations) / len(gap_durations):.1f}s"
        )

        # Identify gaps that look like 3-minute delays
        long_gaps = [g for g in gap_durations if g > 60]
        if long_gaps:
            lines.append(
                f"  Gaps > 60s: {len(long_gaps)}"
            )
            lines.append(
                "  (These likely correspond to the "
                "3-minute step delays)"
            )
    else:
        lines.append("No idle gaps > 2s detected")

    total_to_server = sum(
        c.bytes_to_server for c in sorted_conns
    )
    total_to_client = sum(
        c.bytes_to_client for c in sorted_conns
    )
    lines.append(
        f"Total bytes to server: {total_to_server:,}"
    )
    lines.append(
        f"Total bytes to client: {total_to_client:,}"
    )
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze pcap file for TCP/TLS timing"
    )
    parser.add_argument(
        "pcap_file", help="Path to the pcap file"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=443,
        help="Filter to connections on this port (default: 443)",
    )
    parser.add_argument(
        "--output",
        help="Write output to file instead of stdout",
    )
    args = parser.parse_args()

    connections = analyze_pcap(args.pcap_file, args.port)

    if not connections:
        msg = (
            f"No TCP connections found on port {args.port} "
            f"in {args.pcap_file}"
        )
        print(msg, file=sys.stderr)
        sys.exit(1)

    report = format_results(connections, args.port)

    if args.output:
        from pathlib import Path

        with Path(args.output).open("w") as f:
            f.write(report)
            f.write("\n")
        print(f"Results written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
