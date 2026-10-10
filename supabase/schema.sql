-- CrowdCheck - Supabase schema (routes 177, 170, 190, 17)
-- Fresh project: SQL Editor > New query > paste > Run.
-- Upgrading from the 177-only version? Run migration_002_multi_route.sql instead.
-- (The FastAPI backend also creates/upgrades this table automatically on startup.)

create table if not exists public.crowd_reports (
  id           bigserial primary key,
  route        varchar(10)  not null,
  direction    varchar(20)  not null,
  crowd_level  integer      not null check (crowd_level between 0 and 3),
  stop_name    varchar(80),
  created_at   timestamptz  not null default now()
);

create index if not exists crowd_reports_route_idx   on public.crowd_reports (route);
create index if not exists crowd_reports_created_idx on public.crowd_reports (created_at desc);

-- Only the backend (direct Postgres connection) touches this table.
-- Enabling RLS with no policies blocks the public anon key from reading/writing it.
alter table public.crowd_reports enable row level security;

-- crowd_level: 0 = Seats free, 1 = Standing room, 2 = Packed, 3 = Can't board
-- direction values per route:
--   177: to_kaduwela, to_kollupitiya
--   170: to_athurugiriya, to_pettah
--   190: to_meegoda, to_pettah
--   17 : to_kandy, to_panadura
