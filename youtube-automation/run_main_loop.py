import subprocess
import sys
import time
import argparse


def run_iterations(total_runs: int, delay_between_runs: int = 10, extra_args: list = None):
    """
    Runs 'python -m app.main' a specified number of times.
    Continues to the next iteration even if an iteration fails or returns a non-zero exit code.
    """
    extra = extra_args or []
    print("=" * 65)
    print(f" Starting Multi-Run Runner: {total_runs} total iterations")
    print(f" Target: 'python -m app.main {' '.join(extra)}' | Delay between runs: {delay_between_runs}s")
    print("=" * 65)

    success_count = 0
    failure_count = 0

    for i in range(1, total_runs + 1):
        print(f"\n>>> [Iteration {i}/{total_runs}] Executing 'python -m app.main {' '.join(extra)}'...")
        start_time = time.time()

        try:
            # Run app.main as a subprocess using the current Python environment
            result = subprocess.run([sys.executable, "-m", "app.main"] + extra)
            elapsed = int(time.time() - start_time)

            if result.returncode == 0:
                success_count += 1
                print(f">>> [Iteration {i}/{total_runs}] Finished SUCCESSFULLY in {elapsed}s.")
            else:
                failure_count += 1
                print(f">>> [Iteration {i}/{total_runs}] Exited with error code {result.returncode} in {elapsed}s (continuing)...")

        except KeyboardInterrupt:
            print("\nRunner interrupted manually by user. Stopping.")
            break
        except Exception as e:
            failure_count += 1
            print(f">>> [Iteration {i}/{total_runs}] Exception occurred: {e} (continuing)...")

        if i < total_runs:
            print(f">>> Waiting {delay_between_runs}s before next iteration...")
            time.sleep(delay_between_runs)

    print("\n" + "=" * 65)
    print(f" Multi-Run Complete!")
    print(f" Total Completed: {i}/{total_runs}")
    print(f" Successes: {success_count} | Failures: {failure_count}")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run 'app.main' a variable number of times.")
    parser.add_argument(
        "-n", "--times",
        type=int,
        default=5,
        help="Number of times to run app.main (default: 5)"
    )
    parser.add_argument(
        "-d", "--delay",
        type=int,
        default=10,
        help="Delay in seconds between runs (default: 10)"
    )
    args, unknown = parser.parse_known_args()

    run_iterations(total_runs=args.times, delay_between_runs=args.delay, extra_args=unknown)

