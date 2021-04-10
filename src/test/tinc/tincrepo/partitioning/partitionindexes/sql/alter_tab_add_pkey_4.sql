-- @author prabhd
-- @modified 2013-08-01 12:00:00
-- @created 2013-08-01 12:00:00
-- @db_name ptidx
-- @tags partitionindexes
-- @negtest True
-- @description ALTER TABLE, Unique index with Primary Key
ALTER TABLE pt_lt_tab ADD primary key(col1,col2);
SELECT * FROM pt_lt_tab WHERE col2 <> 10 ORDER BY col2,col3 LIMIT 5;
