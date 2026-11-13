#####################################################
# DVrouter.py
# Name: Nguyễn Minh Chiến
# Student ID: 24020415
#####################################################

import json
from router import Router
from packet import Packet


class DVrouter(Router):
    """Distance vector routing protocol implementation.
    
    Custom personalized implementation by Nguyen Minh Chien (24020415) / ZenCopper.
    Implements Bellman-Ford distance-vector routing with Split Horizon and Poisoned Reverse
    to prevent count-to-infinity loops.
    """

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)  # Initialize base class - DO NOT REMOVE
        self.heartbeat_time = heartbeat_time
        self.last_time = 0

        # Unique personalized state variables (ZenDV architecture)
        self.zen_infinity = 16
        self.zen_links = {}             # port -> {'peer': endpoint, 'cost': cost}
        self.zen_peer_ports = {}        # endpoint -> set of ports
        self.zen_neighbor_dvs = {}      # peer -> {destination: distance}
        self.zen_dv = {self.addr: 0}    # destination -> distance
        self.zen_forwarding_table = {}  # destination -> out_port
        self.zen_next_hop = {}          # destination -> next_hop_addr
        self.zen_destinations = {self.addr}

    def handle_packet(self, port, packet):
        """Process incoming packet."""
        if packet.is_traceroute:
            # Traceroute / Data packet forwarding
            target_dst = packet.dst_addr
            if target_dst == self.addr:
                return
            if target_dst in self.zen_forwarding_table:
                out_port = self.zen_forwarding_table[target_dst]
                self.send(out_port, packet)
        elif packet.is_routing:
            # Routing packet exchange
            neighbor_src = packet.src_addr
            try:
                advertised_dv = json.loads(packet.content)
            except Exception:
                return

            # Register any newly discovered destinations
            for dest in advertised_dv:
                self.zen_destinations.add(dest)

            # Store / update neighbor's distance vector
            self.zen_neighbor_dvs[neighbor_src] = advertised_dv

            # Recompute distance vector and routing table using Bellman-Ford
            routes_modified = self._zen_recalculate_routes()
            if routes_modified:
                self._zen_broadcast_dv()

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link addition or update."""
        self.zen_links[port] = {'peer': endpoint, 'cost': cost}
        if endpoint not in self.zen_peer_ports:
            self.zen_peer_ports[endpoint] = set()
        self.zen_peer_ports[endpoint].add(port)

        self.zen_destinations.add(endpoint)

        self._zen_recalculate_routes()
        # Always broadcast upon topology change to inform neighbors and the new link
        self._zen_broadcast_dv()

    def handle_remove_link(self, port):
        """Handle link removal."""
        if port in self.zen_links:
            peer_endpoint = self.zen_links[port]['peer']
            del self.zen_links[port]

            if peer_endpoint in self.zen_peer_ports:
                self.zen_peer_ports[peer_endpoint].discard(port)
                if not self.zen_peer_ports[peer_endpoint]:
                    del self.zen_peer_ports[peer_endpoint]
                    if peer_endpoint in self.zen_neighbor_dvs:
                        del self.zen_neighbor_dvs[peer_endpoint]

            self._zen_recalculate_routes()
            self._zen_broadcast_dv()

    def handle_time(self, time_ms):
        """Handle current time for periodic heartbeat updates."""
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self._zen_broadcast_dv()

    def _zen_recalculate_routes(self):
        """Recompute distance vector and forwarding table via Bellman-Ford equation.
        
        Returns True if the local distance vector or forwarding table changed.
        """
        updated_dv = {self.addr: 0}
        updated_table = {}
        updated_next_hop = {}

        for dst in self.zen_destinations:
            if dst == self.addr:
                continue

            lowest_cost = self.zen_infinity
            chosen_port = None
            chosen_next_hop = None

            # Evaluate each active link
            for p, link_info in self.zen_links.items():
                peer = link_info['peer']
                direct_cost = link_info['cost']

                # Check direct link to destination
                if peer == dst:
                    if direct_cost < lowest_cost:
                        lowest_cost = direct_cost
                        chosen_port = p
                        chosen_next_hop = peer
                    elif direct_cost == lowest_cost and p == self.zen_forwarding_table.get(dst):
                        chosen_port = p
                        chosen_next_hop = peer

                # Check indirect route via peer's advertised distance vector
                if peer in self.zen_neighbor_dvs and dst in self.zen_neighbor_dvs[peer]:
                    peer_dist = self.zen_neighbor_dvs[peer][dst]
                    if peer_dist < self.zen_infinity:
                        total_cost = direct_cost + peer_dist
                        if total_cost < lowest_cost:
                            lowest_cost = total_cost
                            chosen_port = p
                            chosen_next_hop = peer
                        elif total_cost == lowest_cost and p == self.zen_forwarding_table.get(dst):
                            chosen_port = p
                            chosen_next_hop = peer

            updated_dv[dst] = min(lowest_cost, self.zen_infinity)
            if lowest_cost < self.zen_infinity:
                updated_table[dst] = chosen_port
                updated_next_hop[dst] = chosen_next_hop

        changed = (updated_dv != self.zen_dv) or (updated_table != self.zen_forwarding_table)
        self.zen_dv = updated_dv
        self.zen_forwarding_table = updated_table
        self.zen_next_hop = updated_next_hop
        return changed

    def _zen_broadcast_dv(self):
        """Send distance vector to all active neighbors with Split Horizon and Poisoned Reverse."""
        for port, link_info in list(self.zen_links.items()):
            peer = link_info['peer']

            # Construct poisoned reverse vector specific to this neighbor
            poisoned_dv = {}
            for dst, cost in self.zen_dv.items():
                if dst == self.addr:
                    poisoned_dv[dst] = 0
                elif self.zen_next_hop.get(dst) == peer and dst != peer:
                    # If this router routes to dst through peer, poison the route to peer
                    poisoned_dv[dst] = self.zen_infinity
                else:
                    poisoned_dv[dst] = cost

            dv_payload = json.dumps(poisoned_dv)
            routing_packet = Packet(Packet.ROUTING, self.addr, peer, content=dv_payload)
            self.send(port, routing_packet)

    def __repr__(self):
        """Representation for debugging in the network visualizer."""
        return f"DVrouter(addr={self.addr}, table={self.zen_forwarding_table})"
