-- 
-- @description Interconncet flow control test case: single guc value
-- @created 2012-11-06
-- @modified 2012-11-06
-- @tags executor
-- @gpdb_version [4.2.3.0,main]

-- Create a table
CREATE TABLE small_table(dkey INT, jkey INT, rval REAL, tval TEXT default 'abcdefghijklmnopqrstuvwxyz') DISTRIBUTED BY (dkey);

-- Generate some data
INSERT INTO small_table VALUES(generate_series(1, 5000), generate_series(5001, 10000), sqrt(generate_series(5001, 10000)));

-- Functional tests
-- Skew with gather+redistribute
SELECT ROUND(foo.rval * foo.rval)::INT % 30 AS rval2, COUNT(*) AS count, SUM(length(foo.tval)) AS sum_len_tval
  FROM (SELECT 5001 AS jkey, rval, tval FROM small_table ORDER BY dkey LIMIT 3000) foo
    JOIN small_table USING(jkey)
  GROUP BY rval2
  ORDER BY rval2;

-- Set GUC value to its min value 
set gp_interconnect_min_retries_before_timeout = 1;
show gp_interconnect_min_retries_before_timeout;
SELECT ROUND(foo.rval * foo.rval)::INT % 30 AS rval2, COUNT(*) AS count, SUM(length(foo.tval)) AS sum_len_tval
  FROM (SELECT 5001 AS jkey, rval, tval FROM small_table ORDER BY dkey LIMIT 3000) foo
    JOIN small_table USING(jkey)
  GROUP BY rval2
  ORDER BY rval2;

-- Set GUC value to its max value
set gp_interconnect_min_retries_before_timeout = 4096;
show gp_interconnect_min_retries_before_timeout;
SELECT ROUND(foo.rval * foo.rval)::INT % 30 AS rval2, COUNT(*) AS count, SUM(length(foo.tval)) AS sum_len_tval
  FROM (SELECT 5001 AS jkey, rval, tval FROM small_table ORDER BY dkey LIMIT 3000) foo
    JOIN small_table USING(jkey)
  GROUP BY rval2
  ORDER BY rval2;

-- drop table testemp
DROP TABLE small_table;

RESET gp_interconnect_min_retries_before_timeout;
show gp_interconnect_min_retries_before_timeout;
