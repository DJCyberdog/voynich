"""Owner-run CUDA smoke test on synthetic data; no manuscript input."""
import json
import worker as w
from test_worker import WorkerTests


def main():
    fixture = WorkerTests()
    try:
        fixture.setUp()
        report = w.train(fixture.manifest, fixture.a, fixture.b, fixture.split,
                         fixture.root/'cuda', device='cuda', epochs=2, batch=2)
        w.require(report['environment']['device'] == 'cuda', 'CUDA not used')
        w.require(report['test_n'] == 4, 'Unexpected synthetic test size')
        print(json.dumps(dict(status='PASS', scope='synthetic CUDA training smoke only',
                              hardware=report['environment'], train_n=report['train_n'], test_n=report['test_n'],
                              checkpoint_sha256=report['checkpoint_sha256']), indent=2))
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    main()
