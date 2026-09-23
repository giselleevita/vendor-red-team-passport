# Defensive application and agent testing

The v0.5 runner tests whether an application or tool-using agent preserves authorization and data-handling boundaries across multiple turns. It is designed for systems you own or are authorized to evaluate.

## Safety model

- Tools are never executed. A target may propose a call; the runner validates its name and arguments and returns only the configured synthetic fixture for allowed calls.
- Denied, unknown, malformed, or over-budget calls fail the run. `UNCERTAIN` and execution errors also fail the release gate.
- Canaries must begin with `VRTP_CANARY_`; real credentials and secrets do not belong in scenario files.
- Raw transcripts and tool arguments stay in memory. Persistent evidence contains sanitized excerpts, argument keys, and SHA-256 hashes.
- Curated scenarios use deterministic `none`, `spacing`, and Base64 transport variants. An attacker LLM is not invoked by default.
- Target responses, total turns, total tool calls, retries, and request time are bounded.

## Targets

`openai-compatible-agent` sends OpenAI-style `messages` and function-tool definitions to the configured `/chat/completions` endpoint. Credentials come from `TARGET_API_KEY` or `FEATHERLESS_API_KEY`, never from profiles.

`http-json-app` sends a POST request to a fixed, profile-controlled HTTPS path. Redirects are disabled. Localhost HTTP is allowed for development; arbitrary request-provided target URLs are not accepted by the API.

Request contract:

```json
{
  "scenario_id": "S01",
  "mutation": "none",
  "turn_index": 0,
  "model": "configured-model",
  "messages": [{"role": "user", "content": "synthetic test"}],
  "tools": [],
  "simulation_only": true
}
```

Response contract:

```json
{
  "content": "I cannot help with that request.",
  "tool_calls": []
}
```

The offline `scripted` target is restricted to fixtures under `data/scenarios/` and exists for tests, demonstrations, and reviewer reproduction.

## Running

```bash
vendor-rtp agent-test --profile agent_defensive_demo
```

For a deployed target, copy one of the agent example profiles, set the endpoint, export the required environment credential, and run the same command. Only explicitly authorized staging systems should be tested.
