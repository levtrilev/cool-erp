Приступаем к задаче создания сущности regions в домене sales (префикс sales)

на основе данного выражения создай ddl-выражение create table для справочника регионов. Сущность Регион должна формироваться на основе класса с применением миксинов документа (access && lifecycle). Также создай файлы для backend, работающие с этой таблицей

CREATE TABLE IF NOT EXISTS public.regions
(
    id uuid NOT NULL DEFAULT uuid_generate_v4(),
    name character varying(128) COLLATE pg_catalog."default" NOT NULL,
    capital character varying(128) COLLATE pg_catalog."default",
    code character varying(8) COLLATE pg_catalog."default",
    area character varying(64) COLLATE pg_catalog."default",
    section_id uuid,
    CONSTRAINT regions_pkey PRIMARY KEY (id),
)
