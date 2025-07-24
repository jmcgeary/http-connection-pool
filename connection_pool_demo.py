#!/usr/bin/env python3
"""
Simple Connection Pool Implementation
Two services running locally to demonstrate connection pooling concepts.
"""

import socket
import threading
import time
import queue
from dataclasses import dataclass
from typing import Optional
import json

# =============================================================================
# Service B (Server) - The service we'll connect TO
# =============================================================================

class ServiceB:
    """Simple HTTP-like server that accepts connections"""
    
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.running = False
        
    def start(self):
        """Start the server in a background thread"""
        self.running = True
        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        time.sleep(0.1)  # Give server time to start
        print(f"ServiceB started on {self.host}:{self.port}")
        
    def _run_server(self):
        """Main server loop"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        
        while self.running:
            try:
                client_socket, addr = server_socket.accept()
                # Handle each connection in a new thread
                handler_thread = threading.Thread(
                    target=self._handle_connection, 
                    args=(client_socket, addr)
                )
                handler_thread.daemon = True
                handler_thread.start()
            except OSError:
                break
                
        server_socket.close()
    
    def _handle_connection(self, client_socket, addr):
        """Handle a single client connection - can serve multiple requests"""
        print(f"ServiceB: New connection from {addr}")
        
        try:
            while True:
                # Read request
                data = client_socket.recv(1024)
                if not data:
                    break
                    
                request = data.decode('utf-8').strip()
                print(f"ServiceB: Received request: {request}")
                
                # Simple request processing
                if request.startswith("GET"):
                    response = {
                        "status": "success", 
                        "data": f"Hello from ServiceB at {time.time()}",
                        "connection_id": id(client_socket)
                    }
                else:
                    response = {"status": "error", "message": "Unknown request"}
                
                # Send response
                response_str = json.dumps(response) + "\n"
                client_socket.send(response_str.encode('utf-8'))
                
        except Exception as e:
            print(f"ServiceB: Connection error: {e}")
        finally:
            print(f"ServiceB: Closing connection from {addr}")
            client_socket.close()

# =============================================================================
# Connection Pool Implementation
# =============================================================================

@dataclass(unsafe_hash=True)
class PooledConnection:
    """Represents a pooled connection"""
    socket: socket.socket
    host: str
    port: int
    created_at: float
    last_used: float
    in_use: bool = False
    
    def is_alive(self) -> bool:
        """Check if the connection is still alive"""
        try:
            # Try to get socket error status
            error = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            return error == 0
        except:
            return False
    
    def close(self):
        """Close the underlying socket"""
        try:
            self.socket.close()
        except:
            pass

class SimpleConnectionPool:
    """Simple connection pool implementation"""
    
    def __init__(self, host: str, port: int, max_connections: int = 5):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        
        # Available connections waiting to be used
        self.available_connections = queue.Queue()
        
        # All connections we've created (for tracking)
        self.all_connections = set()
        self.all_connections_lock = threading.Lock()
        
        # Currently borrowed connections
        self.borrowed_connections = set()
        self.borrowed_lock = threading.Lock()
        
    def get_connection(self, timeout: float = 5.0) -> Optional[PooledConnection]:
        """Get a connection from the pool"""
        print(f"Pool: Requesting connection (available: {self.available_connections.qsize()}, "
              f"total: {len(self.all_connections)})")
        
        # Try to get an available connection first
        try:
            conn = self.available_connections.get_nowait()
            if conn.is_alive():
                print(f"Pool: Reusing existing connection {id(conn.socket)}")
                conn.in_use = True
                conn.last_used = time.time()
                with self.borrowed_lock:
                    self.borrowed_connections.add(conn)
                return conn
            else:
                print(f"Pool: Connection {id(conn.socket)} is dead, discarding")
                self._remove_connection(conn)
        except queue.Empty:
            pass
        
        # No available connection - try to create a new one
        with self.all_connections_lock:
            if len(self.all_connections) < self.max_connections:
                conn = self._create_new_connection()
                if conn:
                    print(f"Pool: Created new connection {id(conn.socket)}")
                    self.all_connections.add(conn)
                    with self.borrowed_lock:
                        self.borrowed_connections.add(conn)
                    conn.in_use = True
                    return conn
        
        # Pool is full - wait for a connection to be returned
        print("Pool: Pool is full, waiting for available connection...")
        try:
            conn = self.available_connections.get(timeout=timeout)
            if conn.is_alive():
                with self.borrowed_lock:
                    self.borrowed_connections.add(conn)
                conn.in_use = True
                conn.last_used = time.time()
                return conn
            else:
                self._remove_connection(conn)
                return None
        except queue.Empty:
            print("Pool: Timeout waiting for connection")
            return None
    
    def return_connection(self, conn: PooledConnection):
        """Return a connection to the pool"""
        print(f"Pool: Returning connection {id(conn.socket)}")
        
        with self.borrowed_lock:
            if conn not in self.borrowed_connections:
                raise ValueError("Connection was not borrowed from this pool")
            self.borrowed_connections.remove(conn)
        
        conn.in_use = False
        conn.last_used = time.time()
        
        if conn.is_alive():
            self.available_connections.put(conn)
        else:
            print(f"Pool: Connection {id(conn.socket)} died, removing from pool")
            self._remove_connection(conn)
    
    def _create_new_connection(self) -> Optional[PooledConnection]:
        """Create a new connection to the target service"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            
            now = time.time()
            return PooledConnection(
                socket=sock,
                host=self.host,
                port=self.port,
                created_at=now,
                last_used=now,
                in_use=True
            )
        except Exception as e:
            print(f"Pool: Failed to create connection: {e}")
            return None
    
    def _remove_connection(self, conn: PooledConnection):
        """Remove a connection from the pool entirely"""
        conn.close()
        with self.all_connections_lock:
            self.all_connections.discard(conn)
    
    def get_stats(self):
        """Get pool statistics"""
        return {
            "total_connections": len(self.all_connections),
            "available_connections": self.available_connections.qsize(),
            "borrowed_connections": len(self.borrowed_connections),
            "max_connections": self.max_connections
        }

# =============================================================================
# Service A (Client) - Uses the connection pool
# =============================================================================

class ServiceA:
    """Client service that uses connection pool to talk to ServiceB"""
    
    def __init__(self, service_b_host='localhost', service_b_port=8080):
        self.pool = SimpleConnectionPool(service_b_host, service_b_port, max_connections=3)
    
    def make_request(self, request_data: str) -> Optional[str]:
        """Make a request to ServiceB using the connection pool"""
        conn = self.pool.get_connection()
        if not conn:
            return None
        
        try:
            # Send request
            request = f"GET {request_data}"
            conn.socket.send(request.encode('utf-8'))
            
            # Receive response
            response = conn.socket.recv(1024).decode('utf-8').strip()
            
            return response
            
        except Exception as e:
            print(f"ServiceA: Request failed: {e}")
            return None
        finally:
            # Always return connection to pool
            self.pool.return_connection(conn)
    
    def get_pool_stats(self):
        """Get connection pool statistics"""
        return self.pool.get_stats()

# =============================================================================
# Demo Code
# =============================================================================

def main():
    print("=== Connection Pool Demo ===\n")
    
    # Start ServiceB
    service_b = ServiceB()
    service_b.start()
    
    # Create ServiceA with connection pool
    service_a = ServiceA()
    
    print(f"Initial pool stats: {service_a.get_pool_stats()}")
    print()
    
    # Make some requests to see connection reuse
    for i in range(5):
        print(f"--- Request {i+1} ---")
        response = service_a.make_request(f"/api/data/{i}")
        if response:
            data = json.loads(response)
            print(f"Response: {data}")
            print(f"Connection ID in response: {data.get('connection_id')}")
        
        print(f"Pool stats: {service_a.get_pool_stats()}")
        print()
        time.sleep(1)
    
    print("=== Testing concurrent requests ===")
    
    def worker(worker_id):
        """Worker function for testing concurrent access"""
        for i in range(3):
            response = service_a.make_request(f"/worker/{worker_id}/request/{i}")
            if response:
                data = json.loads(response)
                print(f"Worker {worker_id}: Got response from connection {data.get('connection_id')}")
            time.sleep(0.5)
    
    # Start multiple threads
    threads = []
    for i in range(4):  # More threads than pool size to test waiting
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    print(f"\nFinal pool stats: {service_a.get_pool_stats()}")

if __name__ == "__main__":
    main()