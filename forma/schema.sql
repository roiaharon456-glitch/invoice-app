-- Forma: one table of JSON documents shared by the web app and the WhatsApp agent.
create table if not exists public.docs (
  kind       text        not null,
  key        text        not null,
  data       jsonb       not null,
  updated_at timestamptz not null default now(),
  primary key (kind, key)
);

-- Row level security on, with no policies: the public (anon) key can read nothing.
-- Only the server, using the service_role key, can read and write.
alter table public.docs enable row level security;
