"""
query_generator — standalone module for persona-based health query generation.

Reads persona data from the main HQB benchmark DB; writes generated queries
to its own output DB. No dependency on HQB source code.

Quick start:
    python -m query_generator.generator \\
        --domain general_medical \\
        --topics query_generator/topics/general_medical.txt \\
        --bench-db data/benchmark.db \\
        --out-db output/queries.db

Module layout:
    persona_reader.py       reads synthetic_users from benchmark.db
    output_db.py            creates & manages output queries.db
    llm_client.py           LLM client with proxy + retry
    generator.py            orchestration + CLI entry point
    prompts/
        general_medical.py  prompt template for general_medical domain
    topics/
        general_medical.txt example knowledge catalog topics
"""
