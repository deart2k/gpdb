-- Test if standby will overflow shmNumCommittedGxacts

-- This case test if shmCommittedGxactArray will be overflowed at the following
-- scenario: When a DTX has flushed FORGET COMMITTED XLOG into disk,
-- but didn't change its own state to DTX_STATE_INSERTED_FORGET_COMMITTED.
-- If at this very moment, checkpoint process is calculating DTX info, it
-- will include the DTX into its XLOG record.

create or replace function wait_for_standby_replay (retries int) returns bool as
$$
declare
    i int; /* in func */
    standby_is_up bool; /* in func */
    result bool; /* in func */
begin
    i := 0; /* in func */
    -- Wait until the mirror/standby has replayed up to flush location
    loop
        SELECT flush_location = replay_location INTO result from pg_stat_replication; /* in func */
        if not found then
            return false; /* in func */
        end if; /* in func */
        if result then
            return true; /* in func */
        end if; /* in func */

        if i >= retries then
           return false; /* in func */
        end if; /* in func */
        perform pg_sleep(0.1); /* in func */
        perform pg_stat_clear_snapshot(); /* in func */
        i := i + 1; /* in func */
    end loop; /* in func */
end; /* in func */
$$ language plpgsql;

select wait_for_standby_replay(1200);
create table test_dtx_standby_tbl(c1 int);

-- We have just created a checkpoint.  The next automatic checkpoint
-- will be triggered only after 5 minutes or after CheckPointSegments
-- wal segments.  Neither of that can happen until this test calls
-- explicit checkpoint.
checkpoint;

1: select gp_inject_fault_infinite('dtm_before_insert_forget_comitted', 'suspend', dbid) from gp_segment_configuration where content = -1 and role = 'p';
1: select gp_inject_fault_infinite('checkpoint_after_redo_calculated', 'suspend', dbid) from gp_segment_configuration where content = -1 and role = 'p';
1&: select gp_wait_until_triggered_fault('dtm_before_insert_forget_comitted', 1, dbid) from gp_segment_configuration where content = -1 and role = 'p';

-- record the transaction into checkpoint XLOG and make sure commit forget XLOG is writen
-- before checkpoint XLOG.
2&: insert into test_dtx_standby_tbl select generate_series(1,10);
1<:
1&: select gp_wait_until_triggered_fault('checkpoint_after_redo_calculated', 1, dbid) from gp_segment_configuration where content = -1 and role = 'p';
3&: checkpoint;
1<:
1: select gp_inject_fault_infinite('dtm_before_insert_forget_comitted', 'reset', dbid) from gp_segment_configuration where content = -1 and role = 'p';
2<:
1: select gp_inject_fault_infinite('checkpoint_after_redo_calculated', 'reset', dbid) from gp_segment_configuration where content = -1 and role = 'p';
3<:

-- now the array may have 1 unforggten gid, and we set max_tm_gxacts to 1
1: select gp_inject_fault_infinite('standby_gxacts_overflow', 'skip', dbid) from gp_segment_configuration where content = -1 and role = 'm';

-- this DTX might overflow gxacts array
2: insert into test_dtx_standby_tbl select generate_series(11,20);

-- Wait standby to replay all XLOG
select wait_for_standby_replay(1200);

select gp_inject_fault_infinite('standby_gxacts_overflow', 'reset', dbid) from gp_segment_configuration where content = -1 and role = 'm';
drop table test_dtx_standby_tbl;
drop function wait_for_standby_replay(int);
