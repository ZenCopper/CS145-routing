#####################################################
# LSrouter.py
# Name: Nguyễn Minh Chiến
# Student ID: 24020415
#####################################################

import json
import heapq
from router import Router
from packet import Packet


class LSrouter(Router):
    """Link state routing protocol implementation.
    
    Custom personalized implementation by Nguyen Minh Chien (24020415) / ZenCopper.
    Implements reliable Link-State flooding with sequence numbering and Dijkstra's algorithm
    for shortest-path forwarding table calculation.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_time = 0

        # Unique personalized state variables (ZenLS architecture)
        self.zen_seq = 0
        self.zen_links = {}             # port -> {'peer': peer_endpoint, 'cost': cost}
        self.zen_peer_to_port = {}      # peer_endpoint -> port
        self.zen_seq_records = {}       # router_addr -> highest_sequence_number_seen
        self.zen_link_state_db = {}     # router_addr -> {neighbor: cost}
        self.zen_forwarding_table = {}  # destination -> out_port

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            # Data / Traceroute packet forwarding
            target_dst = packet.dst_addr
            if target_dst == self.addr:
                return
            if target_dst in self.zen_forwarding_table:
                out_port = self.zen_forwarding_table[target_dst]
                self.send(out_port, packet)
        elif packet.is_routing:
            # Link State Packet (LSP) handling
            try:
                lsp_payload = json.loads(packet.content)
            except Exception:
                return

            adv_router = lsp_payload.get("adv_router")
            seq_num = lsp_payload.get("seq")
            links_dict = lsp_payload.get("links")

            if adv_router is None or seq_num is None or links_dict is None:
                return

            # Discard loopback LSPs originated by this router
            if adv_router == self.addr:
                return

            # Check sequence number for freshness
            highest_seen = self.zen_seq_records.get(adv_router, -1)
            if seq_num <= highest_seen:
                # Stale or duplicate LSP, disregard
                return

            # Update link state database with fresher LSP
            self.zen_seq_records[adv_router] = seq_num
            self.zen_link_state_db[adv_router] = links_dict

            # Recompute shortest paths via Dijkstra's algorithm
            self._zen_compute_dijkstra()

            # Controlled flood: forward LSP to all other active neighbor ports
            for out_port in self.zen_links:
                if out_port != port:
                    forwarded_pkt = Packet(Packet.ROUTING, self.addr, "broadcast", content=packet.content)
                    self.send(out_port, forwarded_pkt)

    def handle_new_link(self, port, endpoint, cost):
        """Handle newly connected or updated link."""
        self.zen_links[port] = {'peer': endpoint, 'cost': cost}
        self.zen_peer_to_port[endpoint] = port

        # Increment sequence number for new local topology state
        self.zen_seq += 1
        self.zen_seq_records[self.addr] = self.zen_seq
        self._zen_update_own_lsp()

        # Recompute routing table
        self._zen_compute_dijkstra()

        # Flood our updated LSP to all neighbors
        self._zen_broadcast_own_lsp()

        # Database synchronization: send cached LSPs to the new link so it gets full topology instantly
        self._zen_sync_database_to_port(port)

    def handle_remove_link(self, port):
        """Handle link disconnection."""
        if port in self.zen_links:
            endpoint = self.zen_links[port]['peer']
            del self.zen_links[port]
            if self.zen_peer_to_port.get(endpoint) == port:
                del self.zen_peer_to_port[endpoint]

            self.zen_seq += 1
            self.zen_seq_records[self.addr] = self.zen_seq
            self._zen_update_own_lsp()

            self._zen_compute_dijkstra()
            self._zen_broadcast_own_lsp()

    def handle_time(self, time_ms):
        """Handle current time for periodic heartbeat LSP refreshes."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self.zen_seq += 1
            self.zen_seq_records[self.addr] = self.zen_seq
            self._zen_update_own_lsp()
            self._zen_broadcast_own_lsp()

    def _zen_update_own_lsp(self):
        """Update local link state record in database."""
        own_links = {}
        for link_info in self.zen_links.values():
            peer = link_info['peer']
            cost = link_info['cost']
            # If multiple links exist to same peer, keep the minimum cost
            if peer not in own_links or cost < own_links[peer]:
                own_links[peer] = cost
        self.zen_link_state_db[self.addr] = own_links

    def _zen_broadcast_own_lsp(self):
        """Send local LSP to all connected neighbors."""
        lsp_data = {
            "adv_router": self.addr,
            "seq": self.zen_seq,
            "links": self.zen_link_state_db.get(self.addr, {})
        }
        lsp_content = json.dumps(lsp_data)
        for port in list(self.zen_links.keys()):
            pkt = Packet(Packet.ROUTING, self.addr, "broadcast", content=lsp_content)
            self.send(port, pkt)

    def _zen_sync_database_to_port(self, port):
        """Send all cached LSPs to a specific port for immediate database synchronization."""
        for adv_router, links in self.zen_link_state_db.items():
            if adv_router == self.addr:
                continue
            seq = self.zen_seq_records.get(adv_router, 1)
            cached_lsp = {
                "adv_router": adv_router,
                "seq": seq,
                "links": links
            }
            pkt = Packet(Packet.ROUTING, self.addr, "broadcast", content=json.dumps(cached_lsp))
            self.send(port, pkt)

    def _zen_compute_dijkstra(self):
        """Compute shortest path tree using Dijkstra's algorithm and update forwarding table."""
        dist = {self.addr: 0}
        first_hop = {self.addr: self.addr}
        visited = set()
        pq = [(0, self.addr)]

        while pq:
            current_dist, current_node = heapq.heappop(pq)
            if current_node in visited:
                continue
            visited.add(current_node)

            # Determine outgoing links for current_node
            if current_node == self.addr:
                node_neighbors = self.zen_link_state_db.get(self.addr, {})
            else:
                node_neighbors = self.zen_link_state_db.get(current_node, {})

            for neighbor, link_cost in node_neighbors.items():
                if neighbor in visited:
                    continue
                alternative_dist = current_dist + link_cost
                if alternative_dist < dist.get(neighbor, float('inf')):
                    dist[neighbor] = alternative_dist
                    if current_node == self.addr:
                        first_hop[neighbor] = neighbor
                    else:
                        first_hop[neighbor] = first_hop[current_node]
                    heapq.heappush(pq, (alternative_dist, neighbor))

        # Build forwarding table from first hop map
        new_forwarding_table = {}
        for destination, nxt_hop in first_hop.items():
            if destination != self.addr and nxt_hop in self.zen_peer_to_port:
                new_forwarding_table[destination] = self.zen_peer_to_port[nxt_hop]

        self.zen_forwarding_table = new_forwarding_table

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        return f"LSrouter(addr={self.addr}, table={self.zen_forwarding_table})"
