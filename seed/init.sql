-- Meridian Grid Co. - legacy on-prem contractor/HR database
-- This represents the kind of internal system Cyera's SaaS-only DSPM scanners
-- cannot reach directly, and which the Cyera Privacy Agent connects to
-- from behind the customer's firewall via a Custom API Connection.

CREATE TABLE contractor_pii (
    id              SERIAL PRIMARY KEY,
    full_name       TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT,
    employer        TEXT,
    role            TEXT,
    badge_id        TEXT,
    substation_access TEXT,
    cert_expiry     DATE,
    ssn_last4       TEXT,
    created_at      TIMESTAMP DEFAULT now()
);

INSERT INTO contractor_pii
    (full_name, email, phone, employer, role, badge_id, substation_access, cert_expiry, ssn_last4)
VALUES
    ('Jordan Alvarez', 'jordan.alvarez@fieldpartner.com', '555-0142',
     'Fieldpartner Services LLC', 'Protection Relay Technician', 'BADGE-7841',
     'Substation-14, Substation-22', '2027-03-01', '4821'),
    ('Priya Natarajan', 'priya.n@gridtech-contracting.com', '555-0198',
     'GridTech Contracting', 'Field Engineer', 'BADGE-5502',
     'Substation-09', '2026-11-15', '3390'),
    ('Marcus Webb', 'marcus.webb@fieldpartner.com', '555-0177',
     'Fieldpartner Services LLC', 'Line Crew Supervisor', 'BADGE-6690',
     'Substation-03, Substation-14, Substation-30', '2027-06-20', '9012');
