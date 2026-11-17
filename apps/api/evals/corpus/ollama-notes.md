# Running models locally with Ollama

Ollama serves models over an HTTP API on port 11434 by default. Models are pulled with `ollama pull <name>`.

## Embeddings
Embedding models such as nomic-embed-text turn text into vectors. Similar meanings produce vectors with high cosine similarity, which is what vector databases search over.

## Tool calling
Some chat models support tool calling: the model returns a structured request to call a function, the application runs it, and the result is sent back as a tool message.
