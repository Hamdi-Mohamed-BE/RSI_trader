"""Run the edge-tts CLI with aiohttp's threaded (system) DNS resolver.

aiodns sometimes fails with "Could not contact DNS servers" on this machine while the
system resolver works, so force aiohttp to use the system resolver before edge-tts starts.
Usage is identical to `python -m edge_tts ...`.
"""
import aiohttp.connector
import aiohttp.resolver

aiohttp.resolver.DefaultResolver = aiohttp.resolver.ThreadedResolver
aiohttp.connector.DefaultResolver = aiohttp.resolver.ThreadedResolver

from edge_tts.util import main  # noqa: E402

if __name__ == "__main__":
    main()
