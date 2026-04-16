using DotNetEnv;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

Env.Load(Path.Combine(builder.Environment.ContentRootPath, ".env"));

app.MapGet("/", () => "Hello World!");


app.Run();