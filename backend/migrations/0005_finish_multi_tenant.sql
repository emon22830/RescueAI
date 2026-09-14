-- Closes out 0001_multi_tenant.sql, which was left deliberately half-applied.
--
-- 0001 added `projects.owner_id` as nullable, because at the time there was no
-- signed-up user to assign the existing demo project to. Its steps 3 and 4 — give that
-- project an owner, then require the column — were written as manual follow-ups and
-- never run. The result: `schema.sql` says `owner_id ... not null` while the live
-- database says nullable, and one project belongs to nobody.
--
-- An ownerless project is invisible rather than leaked: every read matches on
-- `owner_id = <the caller>`, and NULL never equals anything. So this is dead data, not
-- a hole — but `not null` cannot be enforced while it exists, and the drift between
-- schema.sql and reality is the kind that bites two years later.
--
-- This is a one-time transition fix, not a pattern. Assigning ownerless rows to the
-- oldest account is only defensible because this database has one real user and is
-- finishing a single-tenant → multi-tenant move. Never do this on a database with
-- several tenants.
--
-- Reversible: `update projects set owner_id = null where id = '<id>'` puts a project
-- back, after dropping the not-null below.

do $$
begin
  if not exists (select 1 from auth.users) then
    raise exception
      'No auth.users yet — sign up first, or this would make owner_id not null with '
      'nothing to point at.';
  end if;

  update projects
     set owner_id = (select id from auth.users order by created_at limit 1)
   where owner_id is null;
end $$;

alter table projects alter column owner_id set not null;
