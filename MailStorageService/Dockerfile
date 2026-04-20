FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

COPY MailStorageService.csproj ./
RUN dotnet restore ./MailStorageService.csproj

COPY . ./
RUN dotnet publish ./MailStorageService.csproj -c Release -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
RUN apt-get update \
    && apt-get install -y --no-install-recommends cifs-utils rsync util-linux \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV ASPNETCORE_URLS=http://+:5001
EXPOSE 5001

COPY --from=build /app/publish ./
ENTRYPOINT ["dotnet", "MailStorageService.dll"]
