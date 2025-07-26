Good conversation here: https://claude.ai/chat/2eafcb22-4483-4d25-a1e2-4b57181e4aec

A connection object has a ref to an os file descriptor, which represents the connection.

It also has a lock so that only a single thread can use it once. When a request is done with the connection, it sets `conn.in_use = False` to return it to the pool

One question with tradeoffs is this: say we're less at less than capacity of connections, so we could hypothetically create a new one. if a request comes in, but all connections are in use, what's the best practice? should we immediately create a new connection, or wait until an existing connection becomes available?

can be a hybrid:
    - have a min number of connections that get eagerly created
    - if resource usage is > X (high utilization, say 80%), then create a new one, otherwise wait
    - if all threads are busy, you could add a short wait time to see if one opens up, then create a new one if not
    - you could check system resources occasionally (this seems a little expensive tho)


need to keep in mind that there's a latency hit when needing to establish a new TCP connection

Apache: https://hc.apache.org/httpcomponents-client-4.5.x/current/tutorial/html/connmgmt.html

Per default this implementation will create no more than 2 concurrent connections per given route and no more 20 connections in total. 

It's one pool per service, the connection manager is the orchestrator, handles creation/deletion, pool management, etc

https://hc.apache.org/httpcomponents-client-4.5.x/current/tutorial/html/connmgmt.html
> The purpose of an HTTP connection manager is to serve as a factory for new HTTP connections, to manage life cycle of persistent connections and to synchronize access to persistent connections making sure that only one thread can have access to a connection at a time

connection manager will block if no available connections, and at the limit. it will block until it times out

Connection health checks:

> If the connection gets closed on the server side, the client side connection is unable to detect the change in the connection state (and react appropriately by closing the socket on its end).

HttpClient tries to mitigate the problem by testing whether the connection is 'stale', that is no longer valid because it was closed on the server side, prior to using the connection for executing an HTTP request. The stale connection check is not 100% reliable.


important for debugging:

- what conditions lead to connection timeouts?

                - **increased downstream latency**: connections are coming in faster than they can be processed by the existing connections (this includes downstream).

                - **surge of requests**: if you have

                - bug that doesn't return connections to the pool

                - either bad downstream host, or DNS issue which increases the load on one downstream host, and since the pool has a limit on threads per host, that specific pool/cap gets exhausted

                - failures/retries which cascades retries downstream, making the bottom most service cascade its bad responses upstream

                - timeout mismatch: server might only keep connections alive for 10 seconds, but client doesn't set this, so the client has connections it thinks are valid, even tho the server has already killed them

mitigation:

- metrics like % utilization, time to acquire connection, etc.

- isolate critical API's into a larger pool, less critical API's into a smaller one

 

### timeouts

connectionRequesTimeout: how long we'll wait to get a connection that already exists in the pool (say if its full)

 

connection timeout: how long to wait when creating a new TCP connection. so this is when the pool creates a new one

 

socket timeout (same as httprequesttimeout): time allowed for data transfer after connection is established. caused by long server processing time, network congestion, db queries taking long etc.

 

difference between connection timeout and socket timeout