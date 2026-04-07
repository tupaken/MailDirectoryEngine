FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

COPY MailDirectoryEngine.csproj ./
RUN dotnet restore ./MailDirectoryEngine.csproj

COPY . ./
RUN dotnet publish ./MailDirectoryEngine.csproj -c Release -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/runtime:10.0 AS final
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /app/publish ./

ENTRYPOINT ["dotnet", "MailDirectoryEngine.dll"]
