"""Fixed native offline parser workload; python -m examples.hot_path_benchmark."""
import base64
import cProfile
import json
from pathlib import Path
import time
from sol_parser.shredstream_client import parse_shred_transaction_with_loaded_addresses

HERE = Path(__file__).parent


def run(config=None, profile=False):
    config = config or json.loads((HERE/'hot_path_benchmark.json').read_text())
    iterations, warmup = config['iterations'], config['warmup']
    if type(iterations) is not int or not 1 <= iterations <= 100000 or type(warmup) is not int or not 0 <= warmup <= 10000:
        raise ValueError('Invalid benchmark iterations/warmup')
    fixtures = json.loads((HERE/'fixtures/pump_shred_routes.json').read_text())
    cases = [(base64.b64decode(f['wire']), f['loaded_writable'], f['loaded_readonly'], len(f['expected'])) for f in fixtures]
    def workload():
        return [len(parse_shred_transaction_with_loaded_addresses(raw, w, r)) for raw,w,r,_ in cases]
    expected = [case[3] for case in cases]
    for _ in range(warmup):
        assert workload() == expected
    if profile:
        profiler = cProfile.Profile()
        profiler.enable()
    times = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        counts = workload()
        times.append((time.perf_counter_ns()-start)/1000)
        assert counts == expected
    if profile:
        profiler.disable()
        profiler.dump_stats('/tmp/python-parser-hotpath.prof')
    times.sort()
    return {'iterations':iterations, 'warmup':warmup, 'transactions_per_iteration':len(cases), 'rpc_calls':0,
            'scope':'six signed wrapped-CPI/ALT wire parses; microseconds per batch',
            **{name:times[int((iterations-1)*p)] for name,p in [('p50',.5),('p95',.95),('p99',.99)]}}


if __name__ == '__main__':
    import sys
    print(json.dumps(run(profile='--profile' in sys.argv),indent=2))
