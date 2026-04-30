using System.Reflection;
using Microsoft.Azure.Cosmos;
using ModelsManagementAPI.Middleware;
using ModelsManagementAPI.Services;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllers();
builder.Services.AddOpenApi();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new Microsoft.OpenApi.OpenApiInfo
    {
        Title = "Models Management API",
        Version = "v1",
        Description = "API for managing AI Foundry model deployments with approval workflow and direct ARM REST API integration."
    });

    var xmlFilename = $"{Assembly.GetExecutingAssembly().GetName().Name}.xml";
    options.IncludeXmlComments(Path.Combine(AppContext.BaseDirectory, xmlFilename));
});

// Register Cosmos DB client
builder.Services.AddSingleton(sp =>
{
    var configuration = sp.GetRequiredService<IConfiguration>();
    var endpoint = configuration["CosmosDb:AccountEndpoint"]!;
    var key = configuration["CosmosDb:AccountKey"]!;
    return new CosmosClient(endpoint, key);
});

// CORS – allow Angular UI
builder.Services.AddCors(options =>
    options.AddDefaultPolicy(policy =>
        policy.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()));

// Register Foundry ARM REST API service
builder.Services.AddHttpClient<IFoundryModelService, FoundryModelService>();

builder.Services.AddScoped<IDeploymentRequestService, CosmosDeploymentRequestService>();

var app = builder.Build();

// Ensure Cosmos DB database and container exist
try
{
    using var scope = app.Services.CreateScope();
    var cosmosClient = scope.ServiceProvider.GetRequiredService<CosmosClient>();
    var configuration = scope.ServiceProvider.GetRequiredService<IConfiguration>();
    var databaseName = configuration["CosmosDb:DatabaseName"]!;
    var containerName = configuration["CosmosDb:ContainerName"]!;

    var database = await cosmosClient.CreateDatabaseIfNotExistsAsync(databaseName);
    await database.Database.CreateContainerIfNotExistsAsync(containerName, "/projectName");
}
catch (Exception ex)
{
    app.Logger.LogWarning(ex, "Failed to initialize Cosmos DB on startup. Ensure connection settings are correct.");
}

// Configure the HTTP request pipeline.
app.UseMiddleware<GlobalExceptionHandlerMiddleware>();
app.UseCors();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.UseSwagger();
    app.UseSwaggerUI(options =>
    {
        options.SwaggerEndpoint("/swagger/v1/swagger.json", "Models Management API v1");
    });
}

app.UseHttpsRedirection();
app.MapControllers();

app.Run();
