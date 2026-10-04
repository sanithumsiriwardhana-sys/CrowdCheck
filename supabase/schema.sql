-- CrowdCheck 177 - Supabase schema
-- Run in Supabase: SQL Editor > New query > paste > Run.
-- (The FastAPI backend also creates this table automatically on startup.)

create table if not exists public.crowd_reports (
  id           bigserial primary key,
  route        varchar(10)  not null,
  direction    varchar(20)  not null check (direction in ('to_sliit', 'from_sliit')),
  crowd_level  integer      not null check (crowd_level between 0 and 3),
  stop_name    varchar(80),
  created_at   timestamptz  not null default now()
);

create index if not exists crowd_reports_route_idx   on public.crowd_reports (route);
create index if not exists crowd_reports_created_idx on public.crowd_reports (created_at desc);

-- Only the backend (direct Postgres connection) touches this table.
-- Enabling RLS with no policies blocks the public anon key from reading/writing it.
alter table public.crowd_reports enable row level security;

-- 0 = Seats free, 1 = Standing room, 2 = Packed, 3 = Can't board
