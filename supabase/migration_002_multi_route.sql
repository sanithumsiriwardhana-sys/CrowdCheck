-- Upgrade an existing 177-only database to multi-route.
-- The backend runs this automatically on startup, so this is only needed
-- if you want to do it by hand in the Supabase SQL Editor.

alter table public.crowd_reports drop constraint if exists crowd_reports_direction_check;

update public.crowd_reports set direction = 'to_kaduwela'
  where route = '177' and direction = 'to_sliit';
update public.crowd_reports set direction = 'to_kollupitiya'
  where route = '177' and direction = 'from_sliit';
