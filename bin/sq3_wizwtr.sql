#!/usr/bin/env sqlite3
-- SQLite3 script
-- create a table `mains` for HomeWizard smart water meter readings

DROP TABLE IF EXISTS mains;


CREATE TABLE mains (
  sample_time   datetime NOT NULL PRIMARY KEY,
  sample_epoch  integer,
  water         integer
  );

-- SQLite3 automatically creates a UNIQUE INDEX on the PRIMARY KEY in the background.
-- So, no index needed.

INSERT INTO mains (sample_time, sample_epoch, water)
       VALUES ('2024-12-25 11:00:00', 1735120800, 891719);
