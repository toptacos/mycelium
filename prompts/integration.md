# integration

**Task:** call a third-party API connection and summarize the response.

## Prompt

```
Use call_api against the 'example' connection with method GET and path '/status'.
Summarize the response for me.

Requirements:
- The connection is configured in mycelium.toml (do not hardcode URLs or tokens)
- Report the HTTP status and interpret the payload
```

## Success criteria

- the call went through the call_api tool
- final message contains the status code and interpretation
