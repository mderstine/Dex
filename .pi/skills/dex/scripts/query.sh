#!/usr/bin/env bash
# Execute a DuckDB query
# Usage: query.sh <sql-query> [--format table|markdown|json]

set -e

SQL_QUERY="${1:-}"
FORMAT="${2:-table}"

if [[ -z "$SQL_QUERY" ]]; then
    echo "Usage: query.sh <sql-query> [--format table|markdown|json]" >&2
    exit 1
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
uv run python -c "
from dex.duckdb_runtime import open_runtime
import sys

with open_runtime() as rt:
    result = rt.query_all('''$SQL_QUERY''')
    
    if '$FORMAT' == 'json':
        import json
        columns = [desc[0] for desc in rt.connection.description] if rt.connection.description else []
        rows = [dict(zip(columns, row)) for row in result]
        print(json.dumps(rows, indent=2, default=str))
    elif '$FORMAT' == 'markdown':
        if not result:
            print('*No results*')
        else:
            columns = [desc[0] for desc in rt.connection.description] if rt.connection.description else []
            header = '| ' + ' | '.join(columns) + ' |'
            separator = '| ' + ' | '.join('---' for _ in columns) + ' |'
            print(header)
            print(separator)
            for row in result:
                print('| ' + ' | '.join(str(v) for v in row) + ' |')
    else:
        for row in result:
            print('\t'.join(str(v) for v in row))
"
