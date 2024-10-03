FROM mcr.microsoft.com/mssql/server:2019-latest

# Установка mssql-tools
USER root

RUN apt-get update && ACCEPT_EULA=Y apt-get install -y \
    curl \
    apt-transport-https \
    gnupg \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && echo "deb [arch=amd64] https://packages.microsoft.com/ubuntu/20.04/prod focal main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y mssql-tools unixodbc-dev \
    && apt-get clean -y

ENV PATH="$PATH:/opt/mssql-tools/bin"

# Копируем скрипт инициализации
COPY init.sql /init.sql

# Запуск SQL Server и выполнение скрипта инициализации
CMD /bin/bash -c "/opt/mssql/bin/sqlservr & sleep 30 && /opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P $SA_PASSWORD -i /init.sql && tail -f /dev/null"
