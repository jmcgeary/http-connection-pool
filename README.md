# HTTP Connection Pool

I was interested in how http connections pools are implemented, so I went through this exercise of building one in Python.

## Features

- **Connection Reuse**: Maintains a pool of TCP connections to avoid the overhead of establishing new connections for each request
- **Thread Safety**: Uses locks and queues to safely manage connections across multiple threads
- **Pool Size Limits**: Configurable maximum connections to prevent resource exhaustion
- **Connection Health Checking**: Validates connections before reuse and removes dead connections
- **Timeout Handling**: Configurable timeouts when waiting for available connections
- **Concurrent Request Support**: Demonstrates handling multiple simultaneous requests

## Components

### ServiceB (Server)
A simple HTTP-like server that accepts connections and processes requests. Each connection can handle multiple sequential requests, demonstrating connection persistence.

### SimpleConnectionPool
The core connection pool implementation featuring:
- `get_connection()`: Retrieves an available connection or creates a new one
- `return_connection()`: Returns a connection to the pool for reuse
- Thread-safe tracking of available and borrowed connections
- Automatic cleanup of dead connections

### ServiceA (Client)
Client service that uses the connection pool to make requests to ServiceB, showing how applications integrate with connection pools.

## Running the Demo

```bash
python3 connection_pool_demo.py
```

The demo shows:
1. **Sequential requests** demonstrating connection reuse
2. **Concurrent requests** with multiple threads competing for connections
3. **Pool statistics** showing connection counts and utilization
4. **Connection IDs** to verify which connections are being reused

## Key Learning Points

- **Connection Overhead**: See how connection reuse improves performance
- **Resource Limits**: Understand how pool size limits prevent resource exhaustion  
- **Thread Contention**: Observe what happens when more threads need connections than the pool allows
- **Connection Lifecycle**: Learn how connections are created, used, and cleaned up

## Implementation Details

- Uses `threading.Lock()` for thread-safe access to shared data structures
- Employs `queue.Queue()` for thread-safe connection storage
- Implements connection health checking via socket error status
- Demonstrates proper resource cleanup and error handling
