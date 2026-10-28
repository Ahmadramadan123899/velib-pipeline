import os  #read .env values
import sys  #to exit with an error code
from pathlib import Path
import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

#The checks
#Each check = (description, severity, SQL that returns ONE number: how many bad rows).
#0 = pass. Anything else = problem.
CHECKS = [
    (
        "latest snapshot is less than 15 minutes old",          #is the pipeline still running?
        "error",
        """SELECT COUNT(*) FROM (SELECT MAX(snapshot_at) AS last FROM station_status) t
           WHERE last IS NULL OR last < now() - interval '15 minutes'""",
    ),
    (
        "no negative bike or dock counts",                      #impossible in real life
        "error",
        """SELECT COUNT(*) FROM station_status
           WHERE bikes_available < 0 OR docks_available < 0
              OR mechanical_available < 0 OR ebike_available < 0""",
    ),
    (
        "bikes = mechanical + ebike",                           #the total must match its parts
        "error",
        """SELECT COUNT(*) FROM station_status
           WHERE bikes_available <> mechanical_available + ebike_available""",
    ),
    (
        "every station in station_status exists in stations",   #replaces the foreign key we skipped
        "error",
        """SELECT COUNT(DISTINCT ss.station_id)
           FROM station_status ss
           LEFT JOIN stations s USING (station_id)
           WHERE s.station_id IS NULL""",
    ),
    (
        "bikes + docks never above capacity",                   #more than the station can hold = strange
        "warning",
        """SELECT COUNT(*) FROM station_status ss
           JOIN stations s USING (station_id)
           WHERE ss.bikes_available + ss.docks_available > s.capacity""",
    ),
    (
        "every snapshot has at least 1400 stations",            #~1519 today; fewer = partial download
        "warning",
        """SELECT COUNT(*) FROM (
               SELECT snapshot_at FROM station_status
               GROUP BY snapshot_at HAVING COUNT(*) < 1400
           ) t""",
    ),
    (
        "stations reported in the last 24h (latest snapshot)",  #the ghost stations from 2017
        "warning",
        """SELECT COUNT(*) FROM station_status
           WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM station_status)
             AND (last_reported IS NULL OR last_reported < snapshot_at - interval '24 hours')""",
    ),
]


def main() -> None:
    errors = 0  #how many "error" checks failed
    with psycopg.connect(
        host="localhost",
        port=5433,
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    ) as conn:
        for description, severity, sql in CHECKS:
            bad_rows = conn.execute(sql).fetchone()[0] #fetchone() = first row; [0] = first column
            if bad_rows == 0:
                status = "PASS"
            elif severity == "error":
                status = "FAIL"
                errors += 1
            else:
                status = "WARN"
            print(f"[{status}] {description}: {bad_rows}")      # e.g. [WARN] stations reported...: 12

    if errors > 0:
        print(f"{errors} check(s) failed")
        sys.exit(1)                                             #exit code 1 = "something went wrong"
    print("All error-level checks passed")


if __name__ == "__main__":
    main()