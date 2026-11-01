-- C R no., year, subject optional at intake (Abhi, 01.11.2026): the engine fills them from the निर्देशपत्र (page 1).
alter table cases alter column cr_no drop not null;
alter table cases alter column cr_year drop not null;
alter table cases alter column subject drop not null;
