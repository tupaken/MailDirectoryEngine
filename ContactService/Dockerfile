FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

COPY ContactService/ContactsService.csproj ContactService/
RUN dotnet restore ContactService/ContactsService.csproj

COPY ContactService/ ContactService/
RUN dotnet publish ContactService/ContactsService.csproj -c Release -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV ASPNETCORE_URLS=http://+:5000
EXPOSE 5000

COPY --from=build /app/publish ./
ENTRYPOINT ["dotnet", "ContactsService.dll"]
