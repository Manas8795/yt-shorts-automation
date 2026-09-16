"""
Runner Loop for YouTube Shorts Uploader
---------------------------------------
Runs 'python uploader.py --limit 1' a specified X number of times.

Usage:
  python run_uploader_loop.py 5
  python run_uploader_loop.py 5 --start-id 19
  python run_uploader_loop.py 5 --skip-ids 18
  python run_uploader_loop.py 10 --delay 15
"""

import sys
import time
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Run YouTube Shorts uploader X times.")
    parser.add_argument("count", type=int, nargs="?", default=None, help="Number of times (X) to run the uploader.")
    parser.add_argument("--delay", type=int, default=10, help="Seconds to wait between iterations (default: 10s).")
    parser.add_argument("--visibility", type=str, default="PUBLIC", choices=["PUBLIC", "PRIVATE", "UNLISTED"], help="Visibility mode.")
    parser.add_argument("--start-id", type=int, default=None, help="Start uploading from this vehicle ID onwards.")
    parser.add_argument("--skip-ids", type=str, default=None, help="Comma-separated vehicle IDs to skip (e.g. 18 or 18,19).")
    args = parser.parse_args()

    iterations = args.count
    if iterations is None:
        try:
            val = input("Enter how many times (X) you want to run the uploader: ").strip()
            iterations = int(val)
        except (ValueError, KeyboardInterrupt, EOFError):
            print("\n[-] Invalid input or cancelled. Exiting.")
            sys.exit(1)

    if iterations <= 0:
        print("[-] Count must be at least 1.")
        sys.exit(1)

    print("=" * 65)
    print(f"STARTING UPLOADER LOOP: {iterations} ITERATION(S)")
    print(f"Command per iteration: python uploader.py --limit 1 --visibility {args.visibility}")
    if args.start_id:
        print(f"Start ID: >= {args.start_id}")
    if args.skip_ids:
        print(f"Skipping IDs: {args.skip_ids}")
    print(f"Cooldown between uploads: {args.delay} seconds")
    print("=" * 65)

    completed = 0
    for i in range(1, iterations + 1):
        print(f"\n>>>>>> RUNNING ITERATION {i} OF {iterations} <<<<<<\n")
        cmd = [sys.executable, "uploader.py", "--limit", "1", "--visibility", args.visibility]
        if args.start_id:
            cmd.extend(["--start-id", str(args.start_id)])
        if args.skip_ids:
            cmd.extend(["--skip-ids", args.skip_ids])

        try:
            res = subprocess.run(cmd)
            if res.returncode == 0:
                completed += 1
                print(f"\n[+] Iteration {i}/{iterations} finished successfully.")
            elif res.returncode == 2:
                print(f"\n{'!' * 65}")
                print(f"[!] YOUTUBE DAILY UPLOAD LIMIT DETECTED.")
                print(f"[!] Stopping loop immediately after {completed} successful upload(s).")
                print(f"[!] YouTube quota is ~15-16 uploads per 24 hours.")
                print(f"[!] Verify your channel phone number in YouTube Studio to raise limit.")
                print(f"{'!' * 65}")
                break
            else:
                print(f"\n{'!' * 65}")
                print(f"[-] Iteration {i}/{iterations} failed with exit code {res.returncode}.")
                print(f"[-] Stopping loop to avoid repeated failed attempts on the same video.")
                print(f"{'!' * 65}")
                break
        except KeyboardInterrupt:
            print("\n[!] User interrupted the loop. Stopping gracefully.")
            break
        except Exception as e:
            print(f"\n[-] Execution error on iteration {i}: {e}")
            break

        if i < iterations:
            print(f"[*] Waiting {args.delay}s before starting next upload...")
            time.sleep(args.delay)

    print("\n" + "=" * 65)
    print(f"LOOP FINISHED: {completed}/{iterations} iterations executed.")
    print("=" * 65)

if __name__ == "__main__":
    main()
