/*-------------------------------------------------------------------------
 *
 * rewriteSupport.h
 *
 *
 *
 * Portions Copyright (c) 1996-2010, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * $PostgreSQL: pgsql/src/include/rewrite/rewriteSupport.h,v 1.32 2010/01/02 16:58:08 momjian Exp $
 *
 *-------------------------------------------------------------------------
 */
#ifndef REWRITESUPPORT_H
#define REWRITESUPPORT_H

/* The ON SELECT rule of a view is always named this: */
#define ViewSelectRuleName	"_RETURN"

extern void SetRelationRuleStatus(Oid relationId, bool relHasRules,
					  bool relIsBecomingView);

extern Oid  get_rewrite_oid(Oid relid, const char *rulename, bool missing_ok);
extern Oid  get_rewrite_oid_without_relid(const char *rulename, Oid *relid);

#endif   /* REWRITESUPPORT_H */
