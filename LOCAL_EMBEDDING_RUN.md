# Optional: sentence-embedding retrieval

The default retriever uses static word vectors (spaCy `en_core_web_md`) and needs no network after setup. To compare against a sentence-transformer embedder, you need network access to huggingface.co for the first model download.

```bash
make setup                                   # creates .venv with Python >= 3.10
.venv/bin/pip install -e ".[st]"
make test                                    # must pass with the static embedder
.venv/bin/python -m eval.run_recall      > eval/results_static.json
.venv/bin/python -m eval.run_recall --st > eval/results_st.json
```

Compare sparse / dense / hybrid recall at k = 1..5, the misses at k = 4, and the gate. The abstain gate (0.05) is lexical, so changing the embedder should affect it little, but check it.

To serve retrieval with the sentence embedder: `DESIGNBENCH_EMBEDDER=st .venv/bin/python -m mcp_server.server`.
