"""
Meridian Grid Co. - Internal System Connector
Maps directly to: Cyera "Custom API Connection"
https://integrations.privacy.cyera.io/docs/integrations/internal-systems-integrations/custom-api-connection

In production this would be the thin adapter a customer writes once to expose
their internal system (here: a legacy on-prem contractor/HR Postgres DB) to
the Cyera Privacy Agent in a way it understands: search-by-identifier and
redact/erase-by-identifier.
"""
import os
import logging
import psycopg2
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format="%(asctime)s connector %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", "postgres"),
    dbname=os.environ.get("DB_NAME", "meridian_hr"),
    user=os.environ.get("DB_USER", "meridian"),
    password=os.environ.get("DB_PASSWORD", "meridian"),
)


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


@app.get("/health")
def health():
    return jsonify(status="ok"), 200


@app.post("/search")
def search():
    """Discover all PII records for a given data subject identifier (email)."""
    body = request.get_json(force=True)
    email = body.get("identifier")
    log.info("SEARCH request for identifier=%s", email)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, full_name, email, phone, employer, role, badge_id,
                  substation_access, cert_expiry, ssn_last4
           FROM contractor_pii WHERE email = %s""",
        (email,),
    )
    cols = [d.name for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    for r in rows:
        r["cert_expiry"] = str(r["cert_expiry"])
    cur.close()
    conn.close()

    log.info("SEARCH found %d record(s) for %s", len(rows), email)
    return jsonify(records=rows), 200


@app.post("/redact")
def redact():
    """Erase/redact all PII fields for a given data subject identifier."""
    body = request.get_json(force=True)
    email = body.get("identifier")
    log.info("REDACT request for identifier=%s", email)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """UPDATE contractor_pii
           SET full_name='[REDACTED]', phone='[REDACTED]', badge_id='[REDACTED]',
               substation_access='[REDACTED]', ssn_last4='[REDACTED]'
           WHERE email = %s""",
        (email,),
    )
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()

    log.info("REDACT affected %d record(s) for %s", affected, email)
    return jsonify(redacted_records=affected), 200


@app.get("/debug/records")
def debug_records():
    """Not part of the real integration contract - lets you show the interviewer
    the before/after state of the underlying DB during the live demo."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""SELECT id, full_name, email, phone, badge_id, substation_access, ssn_last4
                   FROM contractor_pii ORDER BY id""")
    cols = [d.name for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(records=rows), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
