# Services

| Name | Image | Bind | Role |
|---|---|---|---|
| panel | nginx:alpine | 127.0.0.1:18181 | loopback status page |
| cache | redis:7-alpine | 127.0.0.1:16379 | local cache, not LAN-visible |

Both join the `kraken` bridge. Core owns the network; tentacles only plan.
