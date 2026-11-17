-- Una base y un usuario por microservicio: ningún servicio lee la base de otro (sección 3).
CREATE USER auth PASSWORD 'auth_local';            CREATE DATABASE auth_db OWNER auth;
CREATE USER catalogo PASSWORD 'catalogo_local';    CREATE DATABASE catalogo_db OWNER catalogo;
CREATE USER reservas PASSWORD 'reservas_local';    CREATE DATABASE reservas_db OWNER reservas;
CREATE USER ia PASSWORD 'ia_local';                CREATE DATABASE ia_db OWNER ia;
CREATE USER analitica PASSWORD 'analitica_local';  CREATE DATABASE analitica_db OWNER analitica;
