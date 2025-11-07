--
-- PostgreSQL database dump
--

\restrict rF5hJdzcv1d6dOCbTOJLpFuJhsn92CPoXq4XKlG5n84w3ZnDDbM0t1jCQidaemO

-- Dumped from database version 16.10
-- Dumped by pg_dump version 16.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: filestatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.filestatus AS ENUM (
    'ACTIVE',
    'QUARANTINE',
    'DELETED',
    'MISSING'
);


ALTER TYPE public.filestatus OWNER TO postgres;

--
-- Name: transactiontype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.transactiontype AS ENUM (
    'INCOME',
    'EXPENSE'
);


ALTER TYPE public.transactiontype OWNER TO postgres;

--
-- Name: userstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.userstatus AS ENUM (
    'ACTIVE',
    'DISABLED',
    'FROZEN',
    'PENDING',
    'DELETED'
);


ALTER TYPE public.userstatus OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: fileassets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.fileassets (
    id integer NOT NULL,
    fileid character varying(32) NOT NULL,
    filepath character varying(255) NOT NULL,
    type character varying(20) NOT NULL,
    category character varying(20),
    business_id character varying(32) NOT NULL,
    userid character varying(32) NOT NULL,
    status public.filestatus NOT NULL,
    update_userid character varying(32),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.fileassets OWNER TO postgres;

--
-- Name: fileassets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.fileassets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fileassets_id_seq OWNER TO postgres;

--
-- Name: fileassets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.fileassets_id_seq OWNED BY public.fileassets.id;


--
-- Name: loggers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.loggers (
    id integer NOT NULL,
    userid character varying(32) NOT NULL,
    action character varying(255) NOT NULL,
    info character varying(1000) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.loggers OWNER TO postgres;

--
-- Name: loggers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.loggers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.loggers_id_seq OWNER TO postgres;

--
-- Name: loggers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.loggers_id_seq OWNED BY public.loggers.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    transaction_id character varying(32) NOT NULL,
    create_userid character varying(32) NOT NULL,
    update_userid character varying(32),
    amount integer NOT NULL,
    type public.transactiontype NOT NULL,
    remark character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.transactions OWNER TO postgres;

--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transactions_id_seq OWNER TO postgres;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    userid character varying(32) NOT NULL,
    username character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    status public.userstatus NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: user_transaction_summary; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.user_transaction_summary AS
 SELECT u.userid,
    u.username,
    count(t.transaction_id) AS total_transactions,
    sum(
        CASE
            WHEN (t.type = 'INCOME'::public.transactiontype) THEN t.amount
            ELSE 0
        END) AS total_income,
    sum(
        CASE
            WHEN (t.type = 'EXPENSE'::public.transactiontype) THEN t.amount
            ELSE 0
        END) AS total_expense
   FROM (public.users u
     LEFT JOIN public.transactions t ON (((t.create_userid)::text = (u.userid)::text)))
  GROUP BY u.userid, u.username;


ALTER VIEW public.user_transaction_summary OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: fileassets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fileassets ALTER COLUMN id SET DEFAULT nextval('public.fileassets_id_seq'::regclass);


--
-- Name: loggers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.loggers ALTER COLUMN id SET DEFAULT nextval('public.loggers_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: fileassets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.fileassets (id, fileid, filepath, type, category, business_id, userid, status, update_userid, created_at, updated_at) FROM stdin;
1	83333c3549fa419ebae856b6a9ada99f	/static/upload_files/2025/10/17/c5a8abe86299430ab9e5e816b6f00e49.png	transactions	0	c29f308a035e4a3584fd6f5d66d367fe	8af8f3d4a18f4684aa3cb01004d1645a	DELETED	8af8f3d4a18f4684aa3cb01004d1645a	2025-10-17 09:59:24.527852+00	2025-10-20 03:36:51.385039+00
2	9dc4617b5a524b098ea30d1cd8bb024a	/static/upload_files/2025/10/20/73744d156918447aa398e93ebda2e9cb.jpg	transactions	0	c29f308a035e4a3584fd6f5d66d367fe	8af8f3d4a18f4684aa3cb01004d1645a	ACTIVE	\N	2025-10-20 03:36:51.387651+00	\N
3	fdca94be0d0e4d7b8ef5fd465945e176	/static/upload_files/2025/10/20/d7845f62d171499c906860623886b0be.jpg	transactions	0	4f2399dfef194ba9afc7f5eb4d447411	8af8f3d4a18f4684aa3cb01004d1645a	ACTIVE	\N	2025-10-20 06:02:05.155363+00	\N
4	f7f54c9541ee4de891571868242cc405	/static/upload_files/2025/10/14/9332aae518d840c6bd910701f88e8364.png	transactions	0	02129cca0b864b01a41df2ac4d74d5c4	8af8f3d4a18f4684aa3cb01004d1645a	ACTIVE	\N	2025-10-14 00:59:40.923146+00	\N
5	488bee66437e492ab40a99ad91ddb630	/static/upload_files/2025/10/14/1d30dae7c13945548035e050d056f700.png	transactions	0	8d52d58d7cdf4f4189732ffc291a4c44	8af8f3d4a18f4684aa3cb01004d1645a	ACTIVE	\N	2025-10-14 00:59:33.55751+00	\N
6	bce396f8f3564807b4056069f1d7ddac	/static/upload_files/2025/10/14/0652fcb5398c46d9a3a75337363d9a72.png	transactions	0	f17215d4249646cd9f19c89abc2c13be	8af8f3d4a18f4684aa3cb01004d1645a	ACTIVE	\N	2025-10-14 00:51:20.02736+00	\N
7	bd95801588dc46b1a5db6fe0ec4066cd	/static/upload_files/2025/10/10/2203c275b9cb4a648568630ff37d2c07.png	transactions	0		8af8f3d4a18f4684aa3cb01004d1645a	DELETED	\N	2025-10-10 00:27:38.531014+00	\N
8	58fb930775264da881f5fcc6d7c537bf	/static/upload_files/2025/10/14/980395b1e254410e84611ad2c4326059.png	transactions	0	233ad7b0ca7a49d4a4f5056d2e1728f9	8af8f3d4a18f4684aa3cb01004d1645a	ACTIVE	\N	2025-10-14 00:41:20.654877+00	\N
\.


--
-- Data for Name: loggers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.loggers (id, userid, action, info, created_at, updated_at) FROM stdin;
1	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "172.18.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-11-07T03:05:40.665605+00:00"}	2025-11-07 03:05:40.381501+00	\N
2	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-20T07:21:25.796720+00:00"}	2025-10-20 07:21:25.546964+00	\N
3	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-23T03:45:47.385058+00:00"}	2025-10-23 03:45:47.221206+00	\N
4	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:31:39.479078+00:00"}	2025-10-24 05:31:39.570394+00	\N
5	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T06:20:51.443756+00:00"}	2025-10-24 06:20:50.524704+00	\N
6	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T06:20:57.492191+00:00"}	2025-10-24 06:20:56.963055+00	\N
7	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T09:30:45.385120+00:00"}	2025-10-24 09:30:44.916991+00	\N
8	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T09:35:29.864598+00:00"}	2025-10-24 09:35:29.825963+00	\N
9	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-27T09:40:59.794892+00:00"}	2025-10-27 09:40:58.904586+00	\N
10	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-28T07:37:59.214813+00:00"}	2025-10-28 07:37:58.769152+00	\N
11	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-28T07:45:11.316884+00:00"}	2025-10-28 07:45:10.956779+00	\N
12	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-29T06:58:28.625522+00:00"}	2025-10-29 06:58:28.153884+00	\N
13	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-29T07:24:09.716989+00:00"}	2025-10-29 07:24:08.653183+00	\N
14	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-29T07:26:42.156325+00:00"}	2025-10-29 07:26:40.996519+00	\N
15	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-11-05T03:51:02.990848+00:00"}	2025-11-05 03:50:57.060057+00	\N
16	8af8f3d4a18f4684aa3cb01004d1645a	login	iPhone/-; iOS 18.5; web	2025-09-26 03:13:06.593976+00	\N
17	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-20T09:44:27.481231+00:00"}	2025-10-20 09:44:27.203426+00	\N
18	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-23T09:19:22.615306+00:00"}	2025-10-23 09:19:22.178589+00	\N
19	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:41:13.708673+00:00"}	2025-10-24 05:41:12.935444+00	\N
20	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T06:28:47.023741+00:00"}	2025-10-24 06:28:46.431263+00	\N
21	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T09:36:14.498832+00:00"}	2025-10-24 09:36:13.649155+00	\N
22	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-27T09:49:50.673762+00:00"}	2025-10-27 09:49:50.075253+00	\N
23	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-28T08:18:04.516728+00:00"}	2025-10-28 08:18:05.374631+00	\N
24	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-29T07:31:17.340056+00:00"}	2025-10-29 07:31:17.7971+00	\N
25	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-29T07:34:07.246570+00:00"}	2025-10-29 07:34:08.521924+00	\N
26	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-11-05T06:15:29.468881+00:00"}	2025-11-05 06:15:23.578803+00	\N
27	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T05:31:...}	2025-10-10 21:31:39.148661+00	\N
28	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T07:12:...}	2025-10-10 23:12:26.139014+00	\N
29	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T08:14:...}	2025-10-11 00:14:32.112199+00	\N
30	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T08:15:...}	2025-10-11 00:15:02.424873+00	\N
31	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T08:51:...}	2025-10-11 00:51:22.201846+00	\N
32	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T08:51:...}	2025-10-11 00:51:58.651223+00	\N
33	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T09:10:...}	2025-10-11 01:10:43.835527+00	\N
34	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-13T01:30:...}	2025-10-12 17:30:12.751108+00	\N
35	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T03:01:56.560351+00:00"}	2025-10-24 03:01:55.505847+00	\N
36	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T03:17:52.922768+00:00"}	2025-10-24 03:17:53.110566+00	\N
37	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:43:30.755851+00:00"}	2025-10-24 05:43:30.623443+00	\N
38	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T07:36:47.058941+00:00"}	2025-10-24 07:36:46.662169+00	\N
39	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T07:37:18.260015+00:00"}	2025-10-24 07:37:17.868707+00	\N
40	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T07:37:21.262308+00:00"}	2025-10-24 07:37:20.993981+00	\N
41	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T07:37:34.969193+00:00"}	2025-10-24 07:37:35.261216+00	\N
42	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T07:37:37.342540+00:00"}	2025-10-24 07:37:36.475471+00	\N
43	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-27T08:28:30.890023+00:00"}	2025-10-27 08:28:30.381183+00	\N
44	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-27T10:08:43.496929+00:00"}	2025-10-27 10:08:42.582999+00	\N
45	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-29T06:14:48.571215+00:00"}	2025-10-29 06:14:47.826242+00	\N
46	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-13T01:53:...}	2025-10-12 17:53:27.912546+00	\N
47	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-13T02:54:...}	2025-10-12 18:54:16.298586+00	\N
48	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T07:59:...}	2025-10-14 23:59:28.639785+00	\N
49	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T08:00:...}	2025-10-15 00:00:51.901695+00	\N
50	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T08:05:...}	2025-10-15 00:05:36.61227+00	\N
51	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T08:07:...}	2025-10-15 00:07:20.313596+00	\N
52	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T08:10:...}	2025-10-15 00:10:05.182045+00	\N
53	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T08:10:...}	2025-10-15 00:10:26.66443+00	\N
54	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T08:10:...}	2025-10-15 00:10:43.89049+00	\N
55	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T08:12:...}	2025-10-15 00:12:17.131722+00	\N
56	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T09:08:...}	2025-10-15 01:08:27.933398+00	\N
57	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T09:09:...}	2025-10-15 01:09:14.607122+00	\N
58	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T04:00:22.053224+00:00"}	2025-10-24 04:00:21.474135+00	\N
59	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:46:01.608795+00:00"}	2025-10-24 05:46:01.144535+00	\N
60	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:46:13.542034+00:00"}	2025-10-24 05:46:13.708027+00	\N
61	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:46:14.998803+00:00"}	2025-10-24 05:46:15.227494+00	\N
62	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:46:15.638578+00:00"}	2025-10-24 05:46:15.892513+00	\N
63	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:46:22.635595+00:00"}	2025-10-24 05:46:21.889872+00	\N
64	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:47:11.236556+00:00"}	2025-10-24 05:47:11.227521+00	\N
65	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:47:28.097695+00:00"}	2025-10-24 05:47:27.472633+00	\N
66	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T08:06:54.440506+00:00"}	2025-10-24 08:06:53.835201+00	\N
67	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-27T09:21:02.873669+00:00"}	2025-10-27 09:21:02.210848+00	\N
68	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-27T09:28:25.858118+00:00"}	2025-10-27 09:28:25.956432+00	\N
69	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-27T09:29:27.071340+00:00"}	2025-10-27 09:29:27.169781+00	\N
70	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-28T01:42:34.457739+00:00"}	2025-10-28 01:42:33.522756+00	\N
71	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-29T06:15:00.061151+00:00"}	2025-10-29 06:15:00.015957+00	\N
72	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-29T06:20:16.533107+00:00"}	2025-10-29 06:20:16.141221+00	\N
73	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-29T06:21:05.620456+00:00"}	2025-10-29 06:21:04.565613+00	\N
74	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-29T08:09:46.417860+00:00"}	2025-10-29 08:09:45.881966+00	\N
75	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T04:31:00.662237+00:00"}	2025-10-24 04:31:00.86648+00	\N
76	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T04:31:55.585996+00:00"}	2025-10-24 04:31:55.490198+00	\N
77	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T04:31:59.162489+00:00"}	2025-10-24 04:31:59.213415+00	\N
78	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T04:32:15.549398+00:00"}	2025-10-24 04:32:15.016795+00	\N
79	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:48:58.154595+00:00"}	2025-10-24 05:48:57.371437+00	\N
80	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T08:14:14.508413+00:00"}	2025-10-24 08:14:13.753784+00	\N
81	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T01:55:...}	2025-10-09 17:55:59.746442+00	\N
82	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T01:56:...}	2025-10-09 17:56:14.880075+00	\N
83	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T01:59:...}	2025-10-09 17:59:26.992532+00	\N
84	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T02:12:...}	2025-10-09 18:12:27.483272+00	\N
85	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "PC/-; Windows 10 x64; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T03:3...}	2025-10-09 19:38:01.979783+00	\N
86	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T04:00:...}	2025-10-09 20:00:36.954912+00	\N
87	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T05:40:...}	2025-10-09 21:40:56.196475+00	\N
88	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T05:44:...}	2025-10-09 21:44:32.986084+00	\N
89	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T05:50:...}	2025-10-09 21:50:37.56014+00	\N
90	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T05:51:...}	2025-10-09 21:51:19.921136+00	\N
91	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T05:51:...}	2025-10-09 21:51:45.640716+00	\N
92	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T02:17:...}	2025-10-10 18:17:07.464946+00	\N
93	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T04:10:...}	2025-10-10 20:10:07.331362+00	\N
94	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "PC/-; Windows 10 x64; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T04:1...}	2025-10-10 20:11:11.88485+00	\N
95	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T05:30:...}	2025-10-10 21:30:11.153156+00	\N
96	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T05:30:...}	2025-10-10 21:30:12.640449+00	\N
97	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-11T05:30:...}	2025-10-10 21:30:13.814675+00	\N
98	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T10:17:...}	2025-10-15 02:17:28.584197+00	\N
99	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-16T02:58:...}	2025-10-15 18:58:20.834225+00	\N
100	8af8f3d4a18f4684aa3cb01004d1645a	login	iPhone/-; iOS 18.5; web	2025-09-26 05:37:27.646372+00	\N
101	8af8f3d4a18f4684aa3cb01004d1645a	login	iPhone/-; iOS 18.5; web	2025-09-26 05:39:48.278927+00	\N
102	8af8f3d4a18f4684aa3cb01004d1645a	login	iPhone/-; iOS 18.5; web	2025-09-26 05:40:51.844852+00	\N
103	8af8f3d4a18f4684aa3cb01004d1645a	login	SM-G981B/-; Android 13; web	2025-09-27 23:08:11.373541+00	\N
104	8af8f3d4a18f4684aa3cb01004d1645a	login	SM-G981B/-; Android 13; web	2025-09-28 23:32:12.1284+00	\N
105	8af8f3d4a18f4684aa3cb01004d1645a	login	SM-G981B/-; Android 13; web	2025-09-29 01:26:47.14991+00	\N
106	8af8f3d4a18f4684aa3cb01004d1645a	login	SM-G981B/-; Android 13; web	2025-09-29 20:18:24.572402+00	\N
107	8af8f3d4a18f4684aa3cb01004d1645a	login	PC/-; Windows 10 x64; web	2025-10-08 18:30:37.851715+00	\N
108	8af8f3d4a18f4684aa3cb01004d1645a	login	iPhone/-; iOS 18.5; web	2025-10-08 23:56:39.848551+00	\N
109	8af8f3d4a18f4684aa3cb01004d1645a	login	iPhone/-; iOS 18.5; web	2025-10-08 23:56:50.264206+00	\N
110	8af8f3d4a18f4684aa3cb01004d1645a	login	iPhone/-; iOS 18.5; web	2025-10-08 23:56:53.581082+00	\N
111	8af8f3d4a18f4684aa3cb01004d1645a	login	iPhone/-; iOS 18.5; web	2025-10-08 23:56:56.468828+00	\N
112	8af8f3d4a18f4684aa3cb01004d1645a	login	iPhone/-; iOS 18.5; web	2025-10-08 23:56:59.363544+00	\N
113	8af8f3d4a18f4684aa3cb01004d1645a	login	iPhone/-; iOS 18.5; web	2025-10-09 01:44:26.111834+00	\N
114	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-09T10:15:...}	2025-10-09 02:15:44.102129+00	\N
115	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T01:07:...}	2025-10-09 17:07:49.041936+00	\N
116	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T01:13:...}	2025-10-09 17:13:31.921485+00	\N
117	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T01:20:...}	2025-10-09 17:20:24.867476+00	\N
118	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T01:25:...}	2025-10-09 17:25:36.596183+00	\N
119	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-10T01:33:...}	2025-10-09 17:33:52.382101+00	\N
120	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-13T03:47:...}	2025-10-12 19:47:15.164773+00	\N
121	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-14T06:32:...}	2025-10-13 22:32:30.124417+00	\N
122	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-14T07:29:...}	2025-10-13 23:29:00.814736+00	\N
123	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T02:43:...}	2025-10-14 18:43:41.817247+00	\N
124	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T02:44:...}	2025-10-14 18:44:00.339113+00	\N
125	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-15T07:56:...}	2025-10-14 23:56:55.226092+00	\N
126	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "192.168.88.30", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-17T09:26:37.635937+00:00"}	2025-10-17 09:26:41.47673+00	\N
127	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T04:40:16.228461+00:00"}	2025-10-24 04:40:16.153436+00	\N
128	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T04:40:32.343406+00:00"}	2025-10-24 04:40:31.717319+00	\N
129	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "127.0.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-10-24T05:51:34.559620+00:00"}	2025-10-24 05:51:33.712219+00	\N
130	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "172.18.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-11-07T03:16:50.629027+00:00"}	2025-11-07 03:16:50.374597+00	\N
131	8af8f3d4a18f4684aa3cb01004d1645a	login	{"phone_info": "iPhone/-; iOS 18.5; web", "ip": "172.18.0.1", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", "login_time": "2025-11-07T03:18:35.505482+00:00"}	2025-11-07 03:18:35.255155+00	\N
\.


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.transactions (id, transaction_id, create_userid, update_userid, amount, type, remark, created_at, updated_at) FROM stdin;
1	a14e266c618443248cdcf7fe6384c97c	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	EXPENSE	哈哈哈哈	2025-10-10 00:27:38.476533+00	\N
2	233ad7b0ca7a49d4a4f5056d2e1728f9	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	INCOME		2025-10-14 00:41:20.609391+00	\N
3	f17215d4249646cd9f19c89abc2c13be	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	INCOME		2025-10-14 00:51:19.972793+00	\N
4	8d52d58d7cdf4f4189732ffc291a4c44	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	INCOME		2025-10-14 00:59:33.505121+00	\N
5	02129cca0b864b01a41df2ac4d74d5c4	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	INCOME		2025-10-14 00:59:40.878486+00	\N
6	955e2ebb891340b1a0ea607b45866d77	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	INCOME		2025-10-14 01:00:37.74924+00	\N
7	80e8f80e626e4ed097a9f3c18fd5063c	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	INCOME		2025-10-14 01:00:43.186265+00	\N
8	55e2910496834e308c88b2195442ca91	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	EXPENSE	haha	2025-10-14 01:45:34.415328+00	\N
9	9e55f01ccef8499dbba319a9915e7db4	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	EXPENSE	haha	2025-10-14 01:45:34.67224+00	\N
10	0b8400e8c94d4f75b82d429b719db43c	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	EXPENSE	haha	2025-10-14 01:45:35.510182+00	\N
11	8a10cf59297842e6b7eb8c92db7116d1	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	EXPENSE	haha	2025-10-14 01:47:35.835638+00	\N
12	82c1ea5a26cf4a00966df7a350b05a55	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	EXPENSE	haha	2025-10-14 01:47:36.065665+00	\N
13	6960734962f5450d8a8dc963e2547f78	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	EXPENSE	haha	2025-10-14 01:47:36.239189+00	\N
14	859c819345694baeaa9d376935a448a6	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	EXPENSE	haha	2025-10-14 01:47:36.37786+00	\N
15	097b62b7ee994c19a82ad07fbafabe65	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	EXPENSE	haha	2025-10-14 01:47:36.555698+00	\N
16	363e78b98e084c9eaa89b257f79eab27	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	EXPENSE	haha	2025-10-14 01:47:36.700924+00	\N
17	19626999901b4d68a85668e62f452116	8af8f3d4a18f4684aa3cb01004d1645a	\N	1	EXPENSE	haha	2025-10-14 01:47:36.840706+00	\N
18	185e39d207414b478b17640857edfbe3	8af8f3d4a18f4684aa3cb01004d1645a	\N	2	INCOME		2025-10-15 19:41:03.337251+00	\N
19	3d04cecfe48d4d08a882b3a6e3bf7917	8af8f3d4a18f4684aa3cb01004d1645a	\N	2	INCOME		2025-10-15 19:41:08.059567+00	\N
20	c29f308a035e4a3584fd6f5d66d367fe	8af8f3d4a18f4684aa3cb01004d1645a	8af8f3d4a18f4684aa3cb01004d1645a	13	INCOME	测试修改	2025-10-17 09:59:24.506665+00	2025-10-20 03:33:39.485162+00
21	4f2399dfef194ba9afc7f5eb4d447411	8af8f3d4a18f4684aa3cb01004d1645a	8af8f3d4a18f4684aa3cb01004d1645a	12	INCOME	再次测试修改	2025-10-17 09:57:56.934355+00	2025-10-20 06:12:44.369064+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, userid, username, password_hash, status, created_at, updated_at) FROM stdin;
1	8af8f3d4a18f4684aa3cb01004d1645a	kyle	$2b$12$LGG1s8eeBqa/oPyDZSNQDuPyjZEhxwvL2eJDYo36aLjeKMWW4iyr.	ACTIVE	2025-09-25 22:11:23.199586+00	\N
\.


--
-- Name: fileassets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.fileassets_id_seq', 9, true);


--
-- Name: loggers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.loggers_id_seq', 131, true);


--
-- Name: transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.transactions_id_seq', 22, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 2, true);


--
-- Name: fileassets fileassets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fileassets
    ADD CONSTRAINT fileassets_pkey PRIMARY KEY (id);


--
-- Name: loggers loggers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.loggers
    ADD CONSTRAINT loggers_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_fileassets_business_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_fileassets_business_id ON public.fileassets USING btree (business_id);


--
-- Name: ix_fileassets_fileid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_fileassets_fileid ON public.fileassets USING btree (fileid);


--
-- Name: ix_fileassets_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_fileassets_id ON public.fileassets USING btree (id);


--
-- Name: ix_fileassets_userid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_fileassets_userid ON public.fileassets USING btree (userid);


--
-- Name: ix_loggers_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_loggers_id ON public.loggers USING btree (id);


--
-- Name: ix_loggers_userid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_loggers_userid ON public.loggers USING btree (userid);


--
-- Name: ix_transactions_create_userid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_transactions_create_userid ON public.transactions USING btree (create_userid);


--
-- Name: ix_transactions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_transactions_id ON public.transactions USING btree (id);


--
-- Name: ix_transactions_transaction_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_transactions_transaction_id ON public.transactions USING btree (transaction_id);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_userid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_userid ON public.users USING btree (userid);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- PostgreSQL database dump complete
--

\unrestrict rF5hJdzcv1d6dOCbTOJLpFuJhsn92CPoXq4XKlG5n84w3ZnDDbM0t1jCQidaemO

